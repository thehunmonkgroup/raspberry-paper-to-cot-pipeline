```sh
watch "sqlite3 papers.db 'select count(id) from papers where processing_status = \"cleaned\"'"

watch "sqlite3 papers.db 'select count(id) from papers; select count(paper_id) from paper_categories;'"

watch "sqlite3 -table papers.db 'SELECT pc.category, COUNT(p.id) AS count FROM papers p INNER JOIN paper_categories pc ON p.id = pc.paper_id WHERE p.processing_status = \"cleaned\" GROUP BY pc.category ORDER BY count DESC'"

sqlite3 -table papers.db 'SELECT pc.category, COUNT(p.id) AS count FROM papers p INNER JOIN paper_categories pc ON p.id = pc.paper_id WHERE p.processing_status = "cleaned" GROUP BY pc.category ORDER BY count DESC'
```
