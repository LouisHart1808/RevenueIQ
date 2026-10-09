{{ config(materialized='view') }}
select * from {{ source('raw', 'category_translation') }}
