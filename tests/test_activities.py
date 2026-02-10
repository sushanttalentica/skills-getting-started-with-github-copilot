"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to known state before each test"""
    # Save original state
    original_activities = {
        k: {
            "description": v["description"],
            "schedule": v["schedule"],
            "max_participants": v["max_participants"],
            "participants": v["participants"].copy()
        }
        for k, v in activities.items()
    }
    
    yield
    
    # Restore original state
    for k, v in original_activities.items():
        activities[k]["participants"] = v["participants"]


class TestActivities:
    """Test the /activities endpoint"""
    
    def test_get_activities(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Tennis Club" in data
        assert "Basketball Team" in data
        assert all("description" in activity for activity in data.values())
        assert all("participants" in activity for activity in data.values())
    
    def test_get_activities_structure(self, client):
        """Test that activity data has correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            assert isinstance(activity_name, str)
            assert "description" in activity
            assert "schedule" in activity
            assert "max_participants" in activity
            assert "participants" in activity
            assert isinstance(activity["participants"], list)


class TestSignup:
    """Test the signup endpoint"""
    
    def test_signup_success(self, client, reset_activities):
        """Test successful signup"""
        response = client.post(
            "/activities/Tennis Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Signed up" in data["message"]
        
        # Verify student was added
        response = client.get("/activities")
        activities_data = response.json()
        assert "newstudent@mergington.edu" in activities_data["Tennis Club"]["participants"]
    
    def test_signup_duplicate_registration(self, client, reset_activities):
        """Test that duplicate signups are rejected"""
        email = "existing@mergington.edu"
        
        # First signup
        response1 = client.post(
            "/activities/Tennis Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Duplicate signup should fail
        response2 = client.post(
            "/activities/Tennis Club/signup",
            params={"email": email}
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]
    
    def test_signup_to_nonexistent_activity(self, client, reset_activities):
        """Test signup to activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_existing_participant(self, client, reset_activities):
        """Test that existing participants can't signup again"""
        response = client.post(
            "/activities/Tennis Club/signup",
            params={"email": "alex@mergington.edu"}
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]


class TestUnregister:
    """Test the unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration"""
        # First signup
        signup_response = client.post(
            "/activities/Debate Team/signup",
            params={"email": "toremove@mergington.edu"}
        )
        assert signup_response.status_code == 200
        
        # Then unregister
        response = client.delete(
            "/activities/Debate Team/unregister",
            params={"email": "toremove@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Unregistered" in data["message"]
        
        # Verify student was removed
        response = client.get("/activities")
        activities_data = response.json()
        assert "toremove@mergington.edu" not in activities_data["Debate Team"]["participants"]
    
    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregister from activity that doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent Club/unregister",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_unregister_not_signed_up(self, client, reset_activities):
        """Test unregistering a student not signed up for activity"""
        response = client.delete(
            "/activities/Tennis Club/unregister",
            params={"email": "notstudent@mergington.edu"}
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]
    
    def test_unregister_existing_participant(self, client, reset_activities):
        """Test unregistering an existing participant"""
        response = client.delete(
            "/activities/Tennis Club/unregister",
            params={"email": "alex@mergington.edu"}
        )
        assert response.status_code == 200
        
        # Verify student was removed
        response = client.get("/activities")
        activities_data = response.json()
        assert "alex@mergington.edu" not in activities_data["Tennis Club"]["participants"]


class TestIntegration:
    """Integration tests for complex scenarios"""
    
    def test_signup_unregister_signup_cycle(self, client, reset_activities):
        """Test full cycle of signup, unregister, and signup again"""
        email = "student@mergington.edu"
        activity = "Drama Club"
        
        # Sign up
        response1 = client.post(f"/activities/{activity}/signup", params={"email": email})
        assert response1.status_code == 200
        
        # Unregister
        response2 = client.delete(f"/activities/{activity}/unregister", params={"email": email})
        assert response2.status_code == 200
        
        # Sign up again (should succeed)
        response3 = client.post(f"/activities/{activity}/signup", params={"email": email})
        assert response3.status_code == 200
        
        # Verify student is registered
        response = client.get("/activities")
        activities_data = response.json()
        assert email in activities_data[activity]["participants"]
    
    def test_multiple_students_signup(self, client, reset_activities):
        """Test multiple students signing up for different activities"""
        students = [
            ("student1@mergington.edu", "Chess Club"),
            ("student2@mergington.edu", "Robotics Club"),
            ("student3@mergington.edu", "Art Studio"),
        ]
        
        # Sign up all students
        for email, activity in students:
            response = client.post(f"/activities/{activity}/signup", params={"email": email})
            assert response.status_code == 200
        
        # Verify all signups
        response = client.get("/activities")
        activities_data = response.json()
        for email, activity in students:
            assert email in activities_data[activity]["participants"]
