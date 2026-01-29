def test_create_ticket(client):
    response = client.post("/api/v1/tickets/", json={
        "title": "Ticket de prueba",
        "description": "Este es un ticket de prueba"
    })
    assert response.status_code == 200
    json_data = response.json()
    data = json_data.get("data", json_data)
    assert data["title"] == "Ticket de prueba"
    assert data["description"] == "Este es un ticket de prueba"
    assert data["status"] == "open"
    assert "id" in data


def test_list_tickets(client):
    client.post("/api/v1/tickets/", json={"title": "Otro ticket", "description": "Descripción"})

    response = client.get("/api/v1/tickets/")
    assert response.status_code == 200
    json_data = response.json()
    page = json_data.get("data", json_data)
    items = page["items"]

    assert isinstance(items, list)
    assert len(items) > 0
    assert "title" in items[0]

    assert page["page"] >= 1
    assert page["size"] >= 1
    assert page["pages"] >= 1


def test_get_ticket_by_id(client):
    post_response = client.post("/api/v1/tickets/", json={"title": "Consulta", "description": "Consulta por ID"})
    post_json = post_response.json()
    post_data = post_json.get("data", post_json)
    ticket_id = post_data["id"]

    get_response = client.get(f"/api/v1/tickets/{ticket_id}")
    assert get_response.status_code == 200
    get_json = get_response.json()
    ticket = get_json.get("data", get_json)
    assert ticket["id"] == ticket_id
    assert ticket["title"] == "Consulta"


def test_update_ticket(client):
    post_response = client.post("/api/v1/tickets/", json={"title": "Actualizar", "description": "Antes del cambio"})
    post_json = post_response.json()
    post_data = post_json.get("data", post_json)
    ticket_id = post_data["id"]

    put_response = client.put(f"/api/v1/tickets/{ticket_id}", json={"status": "in_progress"})
    assert put_response.status_code == 200
    put_json = put_response.json()
    ticket = put_json.get("data", put_json)
    assert ticket["status"] == "in_progress"


def test_get_ticket_not_found(client):
    response = client.get("/api/v1/tickets/99999")
    assert response.status_code == 404
