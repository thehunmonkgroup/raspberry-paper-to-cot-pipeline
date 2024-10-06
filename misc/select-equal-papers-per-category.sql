WITH RECURSIVE
vars(papers_per_category) AS (
  SELECT 10  -- Change this number to adjust papers per category.
),
ranked_papers AS (
  SELECT
    pc.category,
    p.paper_url,
    ROW_NUMBER() OVER (PARTITION BY pc.category ORDER BY RANDOM()) AS category_row_num,
    ROW_NUMBER() OVER (ORDER BY RANDOM()) AS global_row_num
  FROM paper_categories pc
  JOIN papers p ON pc.paper_id = p.id
),
selected_papers AS (
  SELECT category, paper_url, category_row_num, global_row_num
  FROM ranked_papers, vars
  WHERE category_row_num <= vars.papers_per_category
),
final_selection AS (
  SELECT
    category,
    paper_url,
    category_row_num,
    ROW_NUMBER() OVER (PARTITION BY paper_url ORDER BY global_row_num) AS url_row_num
  FROM selected_papers
)
SELECT category, paper_url
FROM final_selection
WHERE url_row_num = 1
ORDER BY category, category_row_num;
