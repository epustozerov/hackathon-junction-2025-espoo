## Fill business plan template

From the project root:

```bash
python3 business_plan/fill_business_plan.py
```

This:

- reads the markdown template from `business_plan/business_plan_template.md`
- uses answers from `business_plan/dummy_filled_business_plan.yaml`
- writes the filled plan to `business_plan/filled_business_plan.md`

You can override defaults, for example:

```bash
python3 business_plan/fill_business_plan.py \
  --template-markdown business_plan/business_plan_template.md \
  --answers-yaml business_plan/dummy_filled_business_plan.yaml \
  --output-markdown business_plan/my_filled_business_plan.md
```


## Create PDF from filled business plan

First install the PDF engine:

```bash
sudo apt install wkhtmltopdf
```

Then convert a filled markdown plan to PDF:

```bash
python3 business_plan/create_pdf_from_filled_business_plan.py \
  business_plan/filled_business_plan.md \
  business_plan/filled_business_plan.pdf
```