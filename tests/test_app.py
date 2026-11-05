from app import create_app


def test_dashboard_and_health():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SECRET_KEY": "test",
    })
    client = app.test_client()
    assert client.get("/").status_code == 200
    assert client.get("/health").json["status"] == "ok"
    assert client.get("/research").status_code == 200
    assert client.get("/news").status_code == 200
