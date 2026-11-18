import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import pandas as pd
from pydantic import BaseModel, Field, model_validator, ValidationError
from fpdf import FPDF
from dotenv import load_dotenv

load_dotenv()

MAPEO_CONCEPTOS = {
    "activo_circulante": "Activo Circulante",
    "inventarios": "Inventarios",
    "activo_total": "Activo Total",
    "pasivo_circulante": "Pasivo Circulante",
    "pasivo_total": "Pasivo Total",
    "capital_contable": "Capital Contable",
    "ventas_netas": "Ventas Netas",
    "utilidad_neta": "Utilidad Neta",
}


# 1. VALIDACIÓN DE DATOS CON PYDANTIC

class EstadosFinancierosSchema(BaseModel):
    """Valida tipos de datos, valores no negativos y la ecuación contable."""
    empresa: str
    activo_circulante: float = Field(ge=0)
    inventarios: float = Field(ge=0)
    activo_total: float = Field(gt=0)
    pasivo_circulante: float = Field(gt=0)
    pasivo_total: float = Field(ge=0)
    capital_contable: float = Field(gt=0)
    ventas_netas: float = Field(gt=0)
    utilidad_neta: float

    @model_validator(mode="after")
    def validar_ecuacion_contable(self):
        # Verifica que Activo Total = Pasivo Total + Capital Contable (margen de 0.01 por redondeo)
        diferencia = abs(self.activo_total - (self.pasivo_total + self.capital_contable))
        if diferencia > 0.01:
            raise ValueError(
                f"Balance descuadrado: Activo ({self.activo_total:,.2f}) != "
                f"Pasivo + Capital ({self.pasivo_total + self.capital_contable:,.2f})"
            )
        if self.inventarios > self.activo_circulante:
            raise ValueError("Los inventarios no pueden superar al Activo Circulante.")
        return self



# =====================================================================
# 3. CÁLCULO DE RAZONES FINANCIERAS
# =====================================================================
def calcular_razones(datos: EstadosFinancierosSchema) -> dict:
    """Procesa las razones de liquidez, endeudamiento y rentabilidad."""
    razon_circulante = datos.activo_circulante / datos.pasivo_circulante
    prueba_acido = (datos.activo_circulante - datos.inventarios) / datos.pasivo_circulante
    endeudamiento_total = (datos.pasivo_total / datos.activo_total) * 100
    apalancamiento = datos.pasivo_total / datos.capital_contable
    margen_neto = (datos.utilidad_neta / datos.ventas_netas) * 100
    roa = (datos.utilidad_neta / datos.activo_total) * 100
    roe = (datos.utilidad_neta / datos.capital_contable) * 100

    return {
        "Razón Circulante (veces)": round(razon_circulante, 2),
        "Prueba del Ácido (veces)": round(prueba_acido, 2),
        "Endeudamiento Total (%)": round(endeudamiento_total, 2),
        "Apalancamiento Pasivo/Capital (veces)": round(apalancamiento, 2),
        "Margen de Utilidad Neta (%)": round(margen_neto, 2),
        "Rendimiento sobre Activos - ROA (%)": round(roa, 2),
        "Rendimiento sobre Capital - ROE (%)": round(roe, 2),
    }


# MENÚ PRINCIPAL DE CONSOLA
def menu_principal():
    archivo_excel = "estados_financieros.xlsx"

    while True:
        print("\n=== MASTER PROGRAMADOR DE RAZONES FINANCIERAS ===")
        print("1. Crear plantilla Excel base (Balance y Estado de Resultados)")
        print("2. Procesar Excel, validar con Pydantic, generar PDF y enviar por Email")
        print("3. Ver esquema JSON de validación (Contrato de datos)")
        print("4. Salir")

        opcion = input("Selecciona una opción: ").strip()

        if opcion == "1":
            crear_excel_base(archivo_excel)

        elif opcion == "2":
            if not os.path.exists(archivo_excel):
                print(f"[AVISO] No existe '{archivo_excel}'. Ejecuta primero la opción 1.")
                continue

            empresa = input("Nombre de la empresa (ej. El Progreso S.A.): ").strip() or "Empresa S.A."
            correo = input("Correo destino para enviar el PDF: ").strip()

            try:
                datos_validados = leer_y_validar_excel(archivo_excel, empresa)
                razones = calcular_razones(datos_validados)

                print("\n--- RESULTADOS CALCULADOS ---")
                for k, v in razones.items():
                    print(f"  * {k}: {v:.2f}")

                ruta_pdf = generar_pdf_reporte(datos_validados, razones)
                print(f"\n[OK] PDF generado al vuelo: {ruta_pdf}")

                if correo:
                    if enviar_pdf_email(correo, empresa, ruta_pdf):
                        print(f"[OK] Reporte enviado exitosamente a {correo}.")

            except ValidationError as ve:
                print(f"\n[ERROR DE VALIDACIÓN PYDANTIC]\n{ve}")
            except Exception as ex:
                print(f"\n[ERROR DE PROCESAMIENTO] {ex}")

        elif opcion == "3":
            # Equivalente en consola a la documentación automática OpenAPI/Swagger
            print(EstadosFinancierosSchema.model_json_schema())

        elif opcion == "4":
            print("Saliendo del sistema...")
            break
        else:
            print("Opción no válida.")


if __name__ == "__main__":
    menu_principal()