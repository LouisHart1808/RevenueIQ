select *, row_number() over(order by order_id, review_id, review_creation_date, review_answer_timestamp) as review_row_id from {{ ref('stg_order_reviews') }}
