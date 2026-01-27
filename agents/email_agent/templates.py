"""Email templates for query results."""

EMAIL_TEMPLATE_HTML = """
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #4CAF50;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }}
        .content {{
            background-color: #f9f9f9;
            padding: 20px;
            border-radius: 0 0 5px 5px;
        }}
        .query-box {{
            background-color: #e8f5e9;
            padding: 15px;
            border-left: 4px solid #4CAF50;
            margin: 20px 0;
            font-family: monospace;
        }}
        .metrics {{
            display: flex;
            justify-content: space-around;
            margin: 20px 0;
        }}
        .metric {{
            text-align: center;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
        }}
        .metric-label {{
            font-size: 12px;
            color: #666;
        }}
        .button {{
            display: inline-block;
            padding: 12px 24px;
            margin: 10px 5px;
            background-color: #4CAF50;
            color: white;
            text-decoration: none;
            border-radius: 5px;
        }}
        .button:hover {{
            background-color: #45a049;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Query Results Ready</h1>
        </div>
        <div class="content">
            <p>Your query has been executed successfully.</p>
            
            <div class="query-box">
                <strong>Query:</strong> {query}
            </div>
            
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value">{row_count}</div>
                    <div class="metric-label">Rows</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{column_count}</div>
                    <div class="metric-label">Columns</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{execution_time}s</div>
                    <div class="metric-label">Execution Time</div>
                </div>
            </div>
            
            <h3>Preview:</h3>
            {preview_table}
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="{download_url}" class="button">Download CSV Results</a>
                <a href="{sql_url}" class="button">Download SQL Query</a>
            </div>
            
            <p style="margin-top: 30px; font-size: 12px; color: #666;">
                The full results are attached to this email and available at the download links above.
            </p>
        </div>
    </div>
</body>
</html>
"""

EMAIL_TEMPLATE_PLAIN = """
Query Results Ready

Your Query: {query}

Results:
- Rows: {row_count}
- Columns: {column_count}
- Execution Time: {execution_time}s

Download CSV Results: {download_url}
Download SQL Query: {sql_url}

The full results are attached to this email.
"""