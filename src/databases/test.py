import asyncio
from client import Client


async def main(a: str = "Test"):
    """_summary_

    Keyword Arguments:
        a {str} -- _description_ (default: {"Test"})
    """
    
    config = {
        "host": "46.160.250.162",
        "port": 2251,
        "username": "logger",
        "password": "logger",
        "database": "logger",
    }

    sql_client = Client(
        host=config["host"],
        port=config["port"],
        username=config["username"],
        password=config["password"],
        database=config["database"],
    )

    print(await sql_client.connect())


if __name__ == "__main__":
    asyncio.run(main())
