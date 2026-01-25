def test_create_ticket(client):
    response = client.post("/tickets/", json={
        "title": "Ticket de prueba",
        "description": "Este es un ticket de prueba"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["result"] is True
    assert data["message"] == "OK"
    ticket = data["data"]
    assert ticket["title"] == "Ticket de prueba"
    assert ticket["description"] == "Este es un ticket de prueba"
    assert ticket["status"] == "open"
    assert "id" in ticket


def test_list_tickets(client):
    client.post("/tickets/", json={"title": "Otro ticket", "description": "Descripción"})

    response = client.get("/tickets/")
    assert response.status_code == 200
    data = response.json()
    assert data["result"] is True
    assert data["message"] == "OK"

    page = data["data"]
    items = page["items"]

    assert isinstance(items, list)
    assert len(items) > 0
    assert "title" in items[0]

    assert page["page"] >= 1
    assert page["size"] >= 1
    assert page["pages"] >= 1


def test_get_ticket_by_id(client):
    post_response = client.post("/tickets/", json={"title": "Consulta", "description": "Consulta por ID"})
    post_data = post_response.json()["data"]
    ticket_id = post_data["id"]

    get_response = client.get(f"/tickets/{ticket_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["result"] is True
    assert data["message"] == "OK"
    ticket = data["data"]
    assert ticket["id"] == ticket_id
    assert ticket["title"] == "Consulta"


def test_update_ticket(client):
    post_response = client.post("/tickets/", json={"title": "Actualizar", "description": "Antes del cambio"})
    ticket_id = post_response.json()["data"]["id"]

    put_response = client.put(f"/tickets/{ticket_id}", json={"status": "in_progress"})
    assert put_response.status_code == 200
    data = put_response.json()
    assert data["result"] is True
    assert data["message"] == "OK"
    ticket = data["data"]
    assert ticket["status"] == "in_progress"


def test_get_ticket_not_found(client):
    response = client.get("/tickets/99999")
    assert response.status_code == 404
    assert response.json()["message"] == "Ticket no encontrado"
