import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("perfiles", "0003_asignar_impresora")]
    operations = [
        migrations.RemoveField("perfilimpresion", "impresora"),
        migrations.RenameField("perfilimpresion", "impresora_ref", "impresora"),
        migrations.AlterField(
            "perfilimpresion", "impresora",
            models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="perfiles", to="impresora.impresora"),
        ),
        migrations.AddConstraint(
            "perfilimpresion",
            models.UniqueConstraint(
                condition=~models.Q(uso_sugerido=""), fields=("impresora", "uso_sugerido"),
                name="un_uso_sugerido_por_impresora",
            ),
        ),
    ]
