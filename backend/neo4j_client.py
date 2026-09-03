from neo4j import GraphDatabase


URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "66760588"


driver = GraphDatabase.driver(
    URI,
    auth=(USERNAME, PASSWORD)
)

# 同步用户角色会话,建立节点和关系
def sync_user_role_session(user_id, role_name, session_id):
    cypher = """
    MERGE (u:User {user_id: $user_id})
    MERGE (r:Role {role_name: $role_name})
    MERGE (s:Session {session_id: $session_id})

    MERGE (u)-[:USES_ROLE]->(r)
    MERGE (u)-[:HAS_SESSION]->(s)
    MERGE (s)-[:FOR_ROLE]->(r)
    """

    with driver.session() as session:
        session.run(
            cypher,
            user_id=user_id,
            role_name=role_name,
            session_id=session_id
        )

def test_connection():
    driver.verify_connectivity()
    print("Neo4j 连接成功")

# 获取所有节点
def get_all_nodes():
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN n")
        for record in result:
            print(record["n"])

if __name__ == "__main__":
    test_connection()
    get_all_nodes()