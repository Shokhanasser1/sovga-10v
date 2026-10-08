from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from .attributes import AttrSpec, canonical_key, validate_values
from .rules import validate_rule
from .search_text import normalize


class Category(models.Model):
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    slug = models.SlugField(unique=True)
    name_ru = models.CharField(max_length=200)
    name_uz = models.CharField(max_length=200)
    is_serialized = models.BooleanField(
        default=False, help_text="Поштучный учёт по IMEI/SN (телефоны, планшеты)"
    )

    class Meta:
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name_ru

    def lineage(self) -> list["Category"]:
        """Цепочка категорий от корня до этой; устойчива к циклам."""
        chain: list[Category] = []
        seen: set[int | None] = set()
        node: Category | None = self
        while node is not None and node.pk not in seen:
            seen.add(node.pk)
            chain.append(node)
            node = node.parent
        return chain[::-1]

    def subtree_ids(self) -> set[int]:
        """pk этой категории и всех её потомков."""
        ids = {self.pk}
        frontier = [self.pk]
        while frontier:
            frontier = list(
                Category.objects.filter(parent_id__in=frontier)
                .exclude(pk__in=ids)
                .values_list("pk", flat=True)
            )
            ids.update(frontier)
        return ids

    def effective_attributes(self) -> list["AttributeDefinition"]:
        """Атрибуты с наследованием; дочерняя категория переопределяет родителя по code."""
        by_code: dict[str, AttributeDefinition] = {}
        for category in self.lineage():
            for definition in category.attribute_definitions.all():
                by_code[definition.code] = definition
        return sorted(by_code.values(), key=lambda d: (d.sort_order, d.code))

    def clean(self) -> None:
        if self.parent is None or self.pk is None:
            return
        if any(category.pk == self.pk for category in self.parent.lineage()):
            raise ValidationError(
                {"parent": "Категория не может быть вложена в саму себя или своего потомка"}
            )


class AttributeDefinition(models.Model):
    class Type(models.TextChoices):
        NUMBER = "number", "Число"
        ENUM = "enum", "Список"
        BOOL = "bool", "Да/нет"
        TEXT = "text", "Текст"

    class Level(models.TextChoices):
        MODEL = "model", "Модель"
        VARIANT = "variant", "Вариант (SKU)"

    class Comparison(models.TextChoices):
        HIGHER_BETTER = "higher_better", "Больше — лучше"
        LOWER_BETTER = "lower_better", "Меньше — лучше"
        NONE = "none", "Не сравнивается"

    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="attribute_definitions"
    )
    code = models.SlugField(max_length=64)
    name_ru = models.CharField(max_length=100)
    name_uz = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=Type.choices)
    unit = models.CharField(max_length=20, blank=True)
    enum_values = models.JSONField(default=list, blank=True)
    level = models.CharField(max_length=10, choices=Level.choices, default=Level.MODEL)
    is_variant_axis = models.BooleanField(default=False)
    is_required = models.BooleanField(default=False)
    is_facet = models.BooleanField(default=False)
    comparison = models.CharField(
        max_length=15, choices=Comparison.choices, default=Comparison.NONE
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["category", "code"], name="unique_attribute_code_per_category"
            )
        ]

    def __str__(self) -> str:
        return f"{self.category} / {self.code}"

    def as_spec(self) -> AttrSpec:
        return AttrSpec(
            code=self.code,
            type=self.type,
            enum_values=tuple(self.enum_values or ()),
            is_required=self.is_required or self.is_variant_axis,
        )

    def clean(self) -> None:
        errors = {}
        if self.is_variant_axis and self.level != self.Level.VARIANT:
            errors["level"] = "Ось вариации должна быть на уровне варианта"
        if self.type == self.Type.ENUM and not self.enum_values:
            errors["enum_values"] = "Для списка нужны допустимые значения"
        if self.comparison != self.Comparison.NONE and self.type != self.Type.NUMBER:
            errors["comparison"] = "Направление сравнения задаётся только для чисел"
        if errors:
            raise ValidationError(errors)


class Status(models.TextChoices):
    DRAFT = "draft", "Черновик"
    ACTIVE = "active", "Активен"
    ARCHIVED = "archived", "В архиве"


class Brand(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.name


class ProductModel(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="product_models")
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="product_models")
    slug = models.SlugField(max_length=200, unique=True)
    name_ru = models.CharField(max_length=200)
    name_uz = models.CharField(max_length=200)
    description_ru = models.TextField(blank=True)
    description_uz = models.TextField(blank=True)
    attributes = models.JSONField(default=dict, blank=True)
    seo_title_ru = models.CharField(max_length=200, blank=True)
    seo_title_uz = models.CharField(max_length=200, blank=True)
    seo_description_ru = models.CharField(max_length=300, blank=True)
    seo_description_uz = models.CharField(max_length=300, blank=True)
    is_accessory = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    search_text = models.TextField(blank=True, editable=False)
    # Кэш для листинга, обновляет run_jobs: цена «от» и есть ли хоть что-то в продаже
    price_from_uzs = models.PositiveBigIntegerField(null=True, blank=True, editable=False)
    is_available = models.BooleanField(default=False, editable=False)

    def __str__(self) -> str:
        return self.name_ru

    def build_search_text(self) -> str:
        """Названия ru/uz, бренд и цепочка категорий — в нормализованном виде, с пробелами по краям."""
        parts = [self.name_ru, self.name_uz]
        if self.brand_id:
            parts.append(self.brand.name)
        if self.category_id:
            for category in self.category.lineage():
                parts += [category.name_ru, category.name_uz]
        return f" {normalize(' '.join(parts))} "

    def save(self, *args, **kwargs) -> None:
        self.search_text = self.build_search_text()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        if self.category_id is None:
            return
        specs = [
            d.as_spec()
            for d in self.category.effective_attributes()
            if d.level == AttributeDefinition.Level.MODEL
        ]
        errors = validate_values(specs, self.attributes)
        if errors:
            raise ValidationError({"attributes": errors})


MXIK_VALIDATOR = RegexValidator(r"^\d{17}$", "ИКПУ (MXIK) — ровно 17 цифр")
DIGITS_VALIDATOR = RegexValidator(r"^\d+$", "Только цифры")


class Variant(models.Model):
    product_model = models.ForeignKey(
        ProductModel, on_delete=models.CASCADE, related_name="variants"
    )
    sku = models.CharField(max_length=64, unique=True)
    barcodes = models.JSONField(default=list, blank=True)
    axes = models.JSONField(default=dict, blank=True)
    axes_key = models.CharField(max_length=500, editable=False)
    attributes = models.JSONField(default=dict, blank=True)
    mxik_code = models.CharField(max_length=17, validators=[MXIK_VALIDATOR])
    package_code = models.CharField(max_length=20, validators=[DIGITS_VALIDATOR])
    weight_g = models.PositiveIntegerField(null=True, blank=True)
    images = models.JSONField(default=list, blank=True)
    giftable = models.BooleanField(default=False, help_text="Может выдаваться подарком")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product_model", "axes_key"], name="unique_variant_axes"
            )
        ]

    def __str__(self) -> str:
        return self.sku

    def save(self, *args, **kwargs) -> None:
        self.axes_key = canonical_key(self.axes)
        super().save(*args, **kwargs)

    def clean(self) -> None:
        if self.product_model_id is None:
            return
        definitions = [
            d
            for d in self.product_model.category.effective_attributes()
            if d.level == AttributeDefinition.Level.VARIANT
        ]
        errors: dict[str, list[str]] = {}
        axis_errors = validate_values(
            [d.as_spec() for d in definitions if d.is_variant_axis], self.axes
        )
        if axis_errors:
            errors["axes"] = axis_errors
        attribute_errors = validate_values(
            [d.as_spec() for d in definitions if not d.is_variant_axis], self.attributes
        )
        if attribute_errors:
            errors["attributes"] = attribute_errors
        if "axes" not in errors:
            self.axes_key = canonical_key(self.axes)
            duplicate = (
                Variant.objects.filter(product_model_id=self.product_model_id, axes_key=self.axes_key)
                .exclude(pk=self.pk)
                .exists()
            )
            if duplicate:
                errors["axes"] = ["Вариант с такими осями уже существует"]
        if errors:
            raise ValidationError(errors)


class AccessoryCompat(models.Model):
    accessory = models.ForeignKey(
        ProductModel, on_delete=models.CASCADE, related_name="compatible_devices"
    )
    device = models.ForeignKey(
        ProductModel, on_delete=models.CASCADE, related_name="explicit_accessories"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["accessory", "device"], name="unique_accessory_device")
        ]

    def __str__(self) -> str:
        return f"{self.accessory} → {self.device}"

    def clean(self) -> None:
        errors = {}
        if self.accessory_id and not self.accessory.is_accessory:
            errors["accessory"] = "Это не аксессуар"
        if self.device_id and self.device.is_accessory:
            errors["device"] = "Устройство не может быть аксессуаром"
        if errors:
            raise ValidationError(errors)


class CompatRule(models.Model):
    accessory = models.ForeignKey(
        ProductModel, on_delete=models.CASCADE, related_name="compat_rules"
    )
    conditions = models.JSONField(
        help_text='[{"attr": "charge_port", "op": "eq", "value": "usb-c"}, '
        '{"attr": "max_charge_w", "op": "lte", "accessory_attr": "output_w"}]'
    )
    note = models.CharField(max_length=200, blank=True)

    def __str__(self) -> str:
        return f"Правило для {self.accessory}"

    def clean(self) -> None:
        errors = validate_rule(self.conditions)
        if errors:
            raise ValidationError({"conditions": errors})


class SearchSynonym(models.Model):
    term = models.CharField(
        max_length=100, unique=True, help_text="Как пишут покупатели: «айфон», «aypon»"
    )
    replacement = models.CharField(max_length=100, help_text="Как в каталоге: «iphone»")

    def __str__(self) -> str:
        return f"{self.term} → {self.replacement}"

    def clean(self) -> None:
        if not normalize(self.term) or not normalize(self.replacement):
            raise ValidationError("Нужны буквы или цифры")

    def save(self, *args, **kwargs) -> None:
        self.term = normalize(self.term)
        self.replacement = normalize(self.replacement)
        super().save(*args, **kwargs)
