from django.core.exceptions import ValidationError
from django.db import models


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
