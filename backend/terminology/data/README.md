`icd10_common.csv` is a short list of frequently used ICD-10-CM codes so search
works out of the box. ICD-10-CM is published by CMS/CDC and is in the public
domain. For the complete code set, download the yearly "Code Descriptions in
Tabular Order" release from https://www.cms.gov/medicare/coding-billing/icd-10-codes
and run `python manage.py load_icd10 icd10cm_order_<year>.txt`.
