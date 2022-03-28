""" test the web interface a bit """

from fastapi.testclient import TestClient

from github_linter.web import app



client = TestClient(app)


def test_read_main():
    """ test that the home page renders """
    response = client.get("/")
    assert response.status_code == 200
    assert b"<title>Github Linter</title>" in response.content
