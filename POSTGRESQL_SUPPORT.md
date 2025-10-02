# PostgreSQL Support in ySights

## Overview

ySights now supports both SQLite and PostgreSQL databases with the same table structure and API. This allows you to choose the database that best fits your needs without changing your code.

## Installation

### Basic Installation (SQLite only)
```bash
pip install ysights
```

### With PostgreSQL Support
```bash
pip install ysights[postgresql]
```

This installs `psycopg2-binary`, which is required for PostgreSQL connectivity.

## Usage

### SQLite (unchanged)
```python
from ysights import YDataHandler

# Initialize with SQLite database file
ydh = YDataHandler('path/to/simulation.db')

# Use all methods as before
agents = ydh.agents()
network = ydh.social_network()
```

### PostgreSQL (new)
```python
from ysights import YDataHandler

# Initialize with PostgreSQL connection string
ydh = YDataHandler('postgresql://user:password@localhost:5432/ysocial_db')

# Use exactly the same methods
agents = ydh.agents()
network = ydh.social_network()
```

## Connection String Format

PostgreSQL connection strings follow the standard format:

```
postgresql://[user]:[password]@[host]:[port]/[database]
```

or

```
postgres://[user]:[password]@[host]:[port]/[database]
```

### Examples:
```python
# Local PostgreSQL
ydh = YDataHandler('postgresql://postgres:mypassword@localhost:5432/ysocial_db')

# Remote PostgreSQL
ydh = YDataHandler('postgresql://user:pass@db.example.com:5432/production')

# With SSL parameters (advanced)
ydh = YDataHandler('postgresql://user:pass@host:5432/db?sslmode=require')
```

## Key Features

1. **Automatic Detection**: The library automatically detects whether you're using SQLite or PostgreSQL based on the connection string.

2. **Transparent API**: All methods work identically regardless of database type. No code changes needed when switching databases.

3. **Query Translation**: SQL queries are automatically translated between SQLite and PostgreSQL dialects (e.g., `?` placeholders become `%s`).

4. **Backward Compatible**: Existing SQLite code continues to work without any modifications.

## Database Schema

The PostgreSQL database must have the same table structure as the SQLite database. Key tables include:

- `user_mgmt`: Agent/user information
- `post`: Posts/tweets created by agents
- `rounds`: Simulation time rounds
- `follow`: Follow/unfollow actions
- `reactions`: User reactions to posts
- `recommendations`: Recommendation system data
- `mentions`: User mentions in posts
- `hashtags` and `post_hashtags`: Hashtag data
- `interests` and `user_interest`: User interests
- `emotions` and `post_emotions`: Emotion data
- `post_toxicity`: Toxicity scores
- And more...

Refer to the example database schema in `docs/notebooks/ysocial_db.db` for the complete structure.

## Migration from SQLite to PostgreSQL

If you have an existing SQLite database and want to migrate to PostgreSQL:

1. **Create PostgreSQL Database**:
   ```sql
   CREATE DATABASE ysocial_db;
   ```

2. **Copy Schema**: Use a tool like `pgloader` or manually create the tables with the same structure.

3. **Import Data**: Export from SQLite and import to PostgreSQL using tools like:
   - `pgloader` (automated)
   - `sqlite3` + `psql` (manual)
   - Python scripts using both libraries

4. **Update Connection String**: Change your YDataHandler initialization:
   ```python
   # Before
   ydh = YDataHandler('simulation.db')
   
   # After
   ydh = YDataHandler('postgresql://user:pass@host:5432/ysocial_db')
   ```

## Performance Considerations

- **SQLite**: Best for single-user scenarios, development, and smaller datasets
- **PostgreSQL**: Better for multi-user access, larger datasets, and production environments

Both databases use the same queries and operations, so performance characteristics depend mainly on your database server configuration and dataset size.

## Testing

The library includes comprehensive tests for both databases:

```bash
# Run all tests
python -m unittest discover -s ysights/test

# Run only PostgreSQL-specific tests
python -m unittest ysights.test.test_postgresql_support
python -m unittest ysights.test.test_postgresql_integration
```

## Troubleshooting

### ImportError: No module named 'psycopg2'

**Solution**: Install PostgreSQL support:
```bash
pip install psycopg2-binary
# or
pip install ysights[postgresql]
```

### Connection Refused / Cannot Connect

**Solution**: Verify:
1. PostgreSQL server is running
2. Host and port are correct
3. Database exists
4. User has proper permissions
5. Firewall allows connection

### Query Syntax Errors

The library automatically handles most dialect differences. If you encounter issues:
1. Ensure your custom queries don't use database-specific syntax
2. Use parameterized queries instead of string formatting
3. Report the issue on GitHub

## Examples

See `examples/database_comparison.py` for a complete example demonstrating both database types.

## Contributing

If you find issues or have suggestions for improving PostgreSQL support, please open an issue or pull request on GitHub.

## Related Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [psycopg2 Documentation](https://www.psycopg.org/docs/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [YSights Documentation](https://ysights.readthedocs.io/)
