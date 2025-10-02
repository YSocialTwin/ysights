"""
Example: Using ySights with both SQLite and PostgreSQL databases

This example demonstrates how ySights can seamlessly work with both
SQLite and PostgreSQL databases using the same API.
"""

from ysights import YDataHandler


def analyze_database(db_connection, db_type):
    """
    Analyze a database using YDataHandler.
    
    Args:
        db_connection (str): Database path (SQLite) or connection string (PostgreSQL)
        db_type (str): Type of database for display purposes
    """
    print(f"\n{'='*60}")
    print(f"Analyzing {db_type} database")
    print(f"{'='*60}\n")
    
    # Initialize handler
    ydh = YDataHandler(db_connection)
    print(f"✓ Connected to {db_type} database")
    print(f"  Database type detected: {ydh.db_type}")
    
    # Get simulation time range
    time_range = ydh.time_range()
    print(f"\n✓ Time Range:")
    print(f"  Min Round: {time_range['min_round']}")
    print(f"  Max Round: {time_range['max_round']}")
    
    # Get agent count
    num_agents = ydh.number_of_agents()
    print(f"\n✓ Agents:")
    print(f"  Total agents: {num_agents}")
    
    # Get first few agents
    agents = ydh.agents()
    agent_list = agents.get_agents()[:3]
    print(f"  Sample agents:")
    for agent in agent_list:
        print(f"    - {agent.username} (ID: {agent.id}, Age: {agent.age})")
    
    # Get posts statistics
    posts = ydh.posts()
    print(f"\n✓ Posts:")
    print(f"  Total posts: {len(posts.get_posts())}")
    
    # Get agent mapping
    mapping = ydh.agent_mapping()
    print(f"\n✓ Agent Mapping:")
    print(f"  Mapped {len(mapping)} agents")
    
    # Custom query example
    query = "SELECT COUNT(*) FROM user_mgmt WHERE age > 30"
    result = ydh.custom_query(query)
    print(f"\n✓ Custom Query:")
    print(f"  Agents over 30: {result[0][0]}")
    
    print(f"\n{'='*60}")
    print(f"{db_type} analysis complete!")
    print(f"{'='*60}\n")


def main():
    """Main function to demonstrate both database types."""
    
    print("\nySights Database Comparison Example")
    print("====================================\n")
    print("This example shows how ySights works with both SQLite and PostgreSQL")
    print("databases using the exact same API.\n")
    
    # Example 1: SQLite
    print("\n--- Example 1: SQLite Database ---")
    sqlite_path = "path/to/simulation.db"
    print(f"Connection: {sqlite_path}")
    print("\nUsage:")
    print(f"  ydh = YDataHandler('{sqlite_path}')")
    
    # Example 2: PostgreSQL
    print("\n\n--- Example 2: PostgreSQL Database ---")
    postgres_conn = "postgresql://user:password@localhost:5432/ysocial_db"
    print(f"Connection: {postgres_conn}")
    print("\nUsage:")
    print(f"  ydh = YDataHandler('{postgres_conn}')")
    
    # Benefits
    print("\n\n--- Key Benefits ---")
    print("1. Same API for both database types")
    print("2. No code changes needed to switch databases")
    print("3. Automatic query translation between SQLite and PostgreSQL")
    print("4. Easy migration path from SQLite to PostgreSQL")
    
    # Code example
    print("\n\n--- Complete Example Code ---")
    example_code = '''
from ysights import YDataHandler

# Works with SQLite
ydh_sqlite = YDataHandler('simulation.db')

# Works with PostgreSQL (same methods!)
ydh_postgres = YDataHandler('postgresql://user:pass@host/db')

# All methods work identically
agents = ydh_sqlite.agents()
network = ydh_sqlite.social_network()
posts = ydh_sqlite.posts_by_agent(agent_id=1)

# Same code works with PostgreSQL
agents = ydh_postgres.agents()
network = ydh_postgres.social_network()
posts = ydh_postgres.posts_by_agent(agent_id=1)
'''
    print(example_code)
    
    # To actually run the analysis (uncomment and provide valid connections):
    # analyze_database('path/to/simulation.db', 'SQLite')
    # analyze_database('postgresql://user:password@localhost:5432/ysocial_db', 'PostgreSQL')


if __name__ == "__main__":
    main()
