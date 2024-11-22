# For fetching
```sh
watch "sqlite3 papers.db 'select count(id) from papers; select count(paper_id) from paper_categories;'"

watch "sqlite3 -table papers.db 'SELECT pc.category, COUNT(p.id) AS count FROM papers p INNER JOIN paper_categories pc ON p.id = pc.paper_id GROUP BY pc.category ORDER BY count DESC'"

watch "sqlite3 papers.db 'select count(distinct(category)) as count from paper_categories;'"

sqlite3 -table papers.db 'SELECT pc.category, COUNT(p.id) AS count FROM papers p INNER JOIN paper_categories pc ON p.id = pc.paper_id GROUP BY pc.category ORDER BY count DESC'
```

# For paper status

```sh
watch "sqlite3 -table papers.db 'SELECT processing_status, COUNT(processing_status) AS count FROM papers GROUP BY processing_status'"

sqlite3 -table papers.db 'SELECT processing_status, COUNT(processing_status) AS count FROM papers GROUP BY processing_status'
```
