{{ config(indexes=[{'columns':['order_id']},{'columns':['category','order_id']},{'columns':['seller_id','order_id']}], post_hook='analyze {{ this }}') }}
select i.*, p.category from {{ ref('stg_order_items') }} i left join {{ ref('dim_products') }} p using(product_id)
