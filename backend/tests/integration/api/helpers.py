def post(client, path, body):
    response = client.post(f"/api/v1{path}", json=body)
    assert response.status_code == 201, response.text
    return response.json()
