{% macro guard_release() %}
  {% if env_var('WAREHOUSE_SCHEMA', 'warehouse') == 'warehouse' %}
    {{ exceptions.raise_compiler_error('Build an isolated WAREHOUSE_SCHEMA with scripts/refresh.py; the published warehouse facade is read-only.') }}
  {% endif %}
{% endmacro %}
