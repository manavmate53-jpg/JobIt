# {{ name }}
**{{ location }}** | **{{ phone }}** | **[{{ email }}](mailto:{{ email }})**
- **Interactive PM Product Lab**: [{{ links.pm_product_lab }}]({{ links.pm_product_lab }})
- **Portfolio**: [{{ links.portfolio }}]({{ links.portfolio }})
- **GitHub**: [github.com/manavmate53-jpg]({{ links.github }}) | **LinkedIn**: [{{ links.linkedin }}](https://{{ links.linkedin }})

---

### PROFESSIONAL SUMMARY
{{ summary }}

---

### CORE COMPETENCIES & TOOLING
- **Product Execution**: {{ skills.product_management | join(', ') }}
- **AI & Data Systems**: {{ skills.ai_and_technical | join(', ') }}
- **Operations & Scale**: {{ skills.operations_and_business | join(', ') }}
- **Platforms & Tools**: {{ skills.tools | join(', ') }}

---

### PROFESSIONAL EXPERIENCE

{% for job in work_experience %}
#### **{{ job.role }}** | {{ job.company }}
*{{ job.duration }} | {{ job.location }}*
{% for bullet in job.achievements %}
- {{ bullet }}
{% endfor %}

{% endfor %}

---

### INTERACTIVE BUILDS (LIVE IN PM PRODUCT LAB)
{% for proj in featured_projects[:3] %}
- **{{ proj.name }}** ({{ proj.category }}): {{ proj.summary }} **Key Metric: {{ proj.key_metrics }}.** [Live Demo]({{ proj.url }})
{% endfor %}

---

### EDUCATION & CERTIFICATIONS
- **Education**: {% for edu in education %}{{ edu.degree }}, {{ edu.institution }} ({{ edu.specialization }}){% endfor %}
- **Certifications**: {% for cert in certifications[:4] %}{{ cert.name }} ({{ cert.issuer }}){% if not loop.last %} | {% endif %}{% endfor %}
