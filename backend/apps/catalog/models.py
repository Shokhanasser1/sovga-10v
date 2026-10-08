from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from .attributes import AttrSpec, canonical_key, validate_values


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

    def __str__(self) -> str:
        return self.name_ru

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
