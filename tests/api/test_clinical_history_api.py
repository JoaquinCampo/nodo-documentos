from __future__ import annotations

import pytest


async def _create_document(async_client) -> dict:
    payload = {
        "created_by": "12345678",
        "health_user_ci": "87654321",
        "clinic_name": "Test Clinic",
        "s3_url": "s3://bucket/doc-1",
    }
    response = await async_client.post("/api/documents", json=payload)
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_fetch_clinical_history_returns_documents(async_client):
    created = await _create_document(async_client)

    response = await async_client.get(
        f"/api/clinical-history/{created['health_user_ci']}",
        params={
            "health_worker_ci": "11112222",
            "clinic_name": "Test Clinic",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["doc_id"] == created["doc_id"]


@pytest.mark.asyncio
async def test_fetch_clinical_history_empty_for_nonexistent_user(async_client):
    """Test that fetching clinical history for a user with no documents returns empty list."""
    response = await async_client.get(
        "/api/clinical-history/99999999",
        params={
            "health_worker_ci": "11112222",
            "clinic_name": "Test Clinic",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data == []


@pytest.mark.asyncio
async def test_fetch_health_worker_access_history_by_worker_ci(async_client):
    """Test fetching access history for a health worker by their CI."""
    # Create a document and access log entry
    created = await _create_document(async_client)

    # Access the clinical history to create a log entry
    await async_client.get(
        f"/api/clinical-history/{created['health_user_ci']}",
        params={
            "health_worker_ci": "11112222",
            "clinic_name": "Test Clinic",
        },
    )

    # Fetch access history for the worker
    response = await async_client.get(
        "/api/clinical-history/health-workers/11112222/access-history"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["health_worker_ci"] == "11112222"
    assert data[0]["health_user_ci"] == created["health_user_ci"]
    assert "requested_at" in data[0]
    assert "viewed" in data[0]


@pytest.mark.asyncio
async def test_fetch_health_worker_access_history_with_patient_filter(async_client):
    """Test fetching access history filtered by patient CI."""
    # Create documents for two different patients
    doc1 = await _create_document(async_client)
    doc2_payload = {
        "created_by": "12345678",
        "health_user_ci": "99998888",
        "clinic_name": "Test Clinic",
        "s3_url": "s3://bucket/doc-2",
    }
    doc2_response = await async_client.post("/api/documents", json=doc2_payload)
    assert doc2_response.status_code == 201
    doc2 = doc2_response.json()

    # Create access logs for both patients
    await async_client.get(
        f"/api/clinical-history/{doc1['health_user_ci']}",
        params={
            "health_worker_ci": "11112222",
            "clinic_name": "Test Clinic",
        },
    )
    await async_client.get(
        f"/api/clinical-history/{doc2['health_user_ci']}",
        params={
            "health_worker_ci": "11112222",
            "clinic_name": "Test Clinic",
        },
    )

    # Fetch access history filtered by first patient
    response = await async_client.get(
        "/api/clinical-history/health-workers/11112222/access-history",
        params={"health_user_ci": doc1["health_user_ci"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    # All entries should be for the filtered patient
    assert all(entry["health_user_ci"] == doc1["health_user_ci"] for entry in data)


@pytest.mark.asyncio
async def test_fetch_health_worker_access_history_empty_for_nonexistent_worker(
    async_client,
):
    """Test that fetching access history for a non-existent worker returns empty list."""
    response = await async_client.get(
        "/api/clinical-history/health-workers/99999999/access-history"
    )

    assert response.status_code == 200
    data = response.json()
    assert data == []


@pytest.mark.asyncio
async def test_fetch_health_worker_access_history_validation_error(async_client):
    """Test that invalid CI format returns validation error."""
    response = await async_client.get(
        "/api/clinical-history/health-workers/123/access-history"
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_fetch_health_user_access_history_by_user_ci(async_client):
    """Test fetching access history for a health user by their CI."""
    # Create a document and access log entry
    created = await _create_document(async_client)

    # Access the clinical history to create a log entry
    await async_client.get(
        f"/api/clinical-history/{created['health_user_ci']}",
        params={
            "health_worker_ci": "11112222",
            "clinic_name": "Test Clinic",
        },
    )

    # Fetch access history for the user
    response = await async_client.get(
        f"/api/clinical-history/health-users/{created['health_user_ci']}/access-history"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["health_user_ci"] == created["health_user_ci"]
    assert data[0]["health_worker_ci"] == "11112222"
    assert "requested_at" in data[0]
    assert "viewed" in data[0]


@pytest.mark.asyncio
async def test_fetch_health_user_access_history_empty_for_nonexistent_user(
    async_client,
):
    """Test that fetching access history for a non-existent user returns empty list."""
    response = await async_client.get(
        "/api/clinical-history/health-users/99999999/access-history"
    )

    assert response.status_code == 200
    data = response.json()
    assert data == []


@pytest.mark.asyncio
async def test_fetch_health_user_access_history_validation_error(async_client):
    """Test that invalid CI format returns validation error."""
    response = await async_client.get(
        "/api/clinical-history/health-users/123/access-history"
    )

    assert response.status_code == 422
