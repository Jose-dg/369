Alegra credentials

Organization id
b7aa7c5c-bdbd-4959-8c98-0ad300d08024

Name
Diem

Email
info@diem.com.co

Is active: True

Token
dd25e346ccfb2b06ff9e

Base ulr
https://api.alegra.com/api/v1

Webhook secret
039b34b8-f58e-42bf-807c-6592a86b0a63

Number template id
19

Auto stamp on create: True

:::

Grupos: empty

:::

ERPNext


Organization ID
812f343d-b1a6-46ae-bb55-7e2c6f945308

ERPNext Site URL
https://latam.v.frappe.cloud/

API Key
457d72662d1184a

API Secret
0530c57b8fa7f2c

Activo: True

:::

Organization


Name: Diem
Slug: diem
Is active: True

Metadata: 

{"fulfillment_gateway": {"currency": "COP", "due_days": 0, "territory": "Colombia", "price_list": "Tarifa Estándar de Venta", "default_uom": "Unidad", "update_stock": true, "item_code_map": {"14633376753": "JUEGO-FIFA-22-PS4", "711719510674": "PS-GIFT-CARD-50", "799366664771": "PS-GIFT-CARD-25", "SKU_PRODUCTO_A": "ERP_CODIGO_A", "SKU_PRODUCTO_B": "ERP_CODIGO_B"}, "naming_series": "SINV-", "tax_account_map": {"IVA 5%": "24080102 - IVA Generado 5% - M4G", "IVA 19%": "24080101 - IVA Generado 19% - M4G"}, "tax_charge_type": "On Net Total", "company_selector": {"domain_map": {"229f93-2.myshopify.com": "TST", "22sde3-2.myshopify.com": "M4G", "229f23sd3-2.myshopify.com": "LAB"}, "tag_prefix": "cia:", "default_company": "M4G"}, "default_customer": "Cliente Contado", "set_posting_time": true, "default_warehouse": "Almacén Principal - M4G", "receivable_account": "130505 - Clientes Nacionales - M4G", "shipping_item_code": "ENVIO", "shipping_item_name": "Costo de Envío", "default_cost_center": "Principal - M4G", "default_tax_account": "240801 - Impuesto sobre las ventas por pagar - M4G", "distributor_company": "Diem", "price_list_currency": "COP", "default_income_account": "4135 - Comercio al por mayor y al por menor - M4G"}}

:::

Shopify

Organization
812f343d-b1a6-46ae-bb55-7e2c6f945308

Shopify Domain
229f93-2.myshopify.com

Webhook Shared Secret
a01f7f39a64695471e37fbe0df8e208733e2c83b11629a3bd2cda3ae695f421a

:::


{
    "fulfillment_gateway": {
        "distributor_company": "Money for gamers",
         "sellers": {
           "shopify": {
             "company_selector": {
               "domain_map": {
                 "229f93-2.myshopify.com": "Diem"
               },
           "default_company": "Diem"
           }
          }
       },
        "default_warehouse": "Almacén Principal - M4G",
        "default_customer": "Cliente Contado",
        "territory": "Colombia",
        "price_list": "Tarifa Estándar de Venta",
        "receivable_account": "130505 - Clientes Nacionales - DM",
        "default_cost_center": "Principal - DM",
        "default_income_account": "4135 - Comercio al por mayor y al por menor - DM",
        "update_stock": true,
        "set_posting_time": true,
        "currency": "COP",
        "price_list_currency": "COP",
        "shipping_item_code": "ENVIO",
        "shipping_item_name": "Costo de Envío",
        "tax_account_map": {
          "IVA 5%": "24080102 - IVA Generado 5% - DM",
          "IVA 19%": "24080101 - IVA Generado 19% - DM"
     },
        "tax_charge_type": "On Net Total",
        "default_tax_account": "240801 - Impuesto sobre las ventas por pagar - DM",
        "naming_series": "SINV-",
        "due_days": 0,
        "default_uom": "Unidad"
      }
    }


    :::

    python manage.py check_erpnext_stock <item_code> --warehouse <warehouse_name> --company <company_name>

    799366084327

    python manage.py check_erpnext_stock "PlayStation Gift Card US$10" --warehouse "Sucursales - MG4" --company "Money for gamers"

   {
  "metadata": {
    "default_warehouse": "Sucursal - M4G",
    "preferred_currency": "COP",
    "notifications": {
      "on_new_order": true,
      "on_stock_change": false
    }
  }
}

1     from apps.companies.models import Company
   2     diem_company = Company.objects.get(name='Diem')

   3. Ahora, el paso más importante. Copia y pega la siguiente línea y presiona Enter. Esto nos mostrará el contenido exacto del campo
       metadata que Django está leyendo:

   1     print(diem_company.metadata)

   Yt6KTTm161