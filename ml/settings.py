from os import getenv


DATABASE_SETTINGS = {
    'url': f'mssql+pyodbc://{getenv("DATABASE_USERNAME")}:{getenv("DATABASE_PASSWORD")}@localhost:1433/STUDY?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=Yes',
    'fast_executemany': True
}
