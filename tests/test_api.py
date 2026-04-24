"""
Comprehensive test suite for Mergington High School API
Tests all endpoints using AAA (Arrange-Act-Assert) pattern
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    original = activities.copy()
    yield
    # Restore original state
    activities.clear()
    activities.update(original)


class TestRootEndpoint:
    """Tests for GET / endpoint"""

    def test_root_redirect(self, client):
        """Test that root redirects to static index.html"""
        # Arrange & Act
        response = client.get("/", follow_redirects=False)

        # Assert
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_all_activities(self, client, reset_activities):
        """Test retrieving all activities"""
        # Arrange & Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

        # Verify all expected activities are present
        expected_activities = [
            "Chess Club", "Programming Class", "Gym Class", "Basketball Team",
            "Tennis Club", "Art Studio", "Drama Club", "Debate Team", "Science Club"
        ]
        for activity in expected_activities:
            assert activity in data

    def test_activity_structure(self, client, reset_activities):
        """Test that each activity has required fields"""
        # Arrange & Act
        response = client.get("/activities")
        data = response.json()

        # Assert
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        # Arrange
        activity_name = "Chess Club"
        email = "newstudent@mergington.edu"
        initial_count = len(activities[activity_name]["participants"])

        # Act
        response = client.post(f"/activities/{activity_name}/signup?email={email}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert email in activities[activity_name]["participants"]
        assert len(activities[activity_name]["participants"]) == initial_count + 1

    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test signup fails for non-existent activity"""
        # Arrange
        activity_name = "Nonexistent Activity"
        email = "student@mergington.edu"

        # Act
        response = client.post(f"/activities/{activity_name}/signup?email={email}")

        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_already_registered(self, client, reset_activities):
        """Test signup fails when student is already registered"""
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"  # Already registered

        # Act
        response = client.post(f"/activities/{activity_name}/signup?email={email}")

        # Assert
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_multiple_students(self, client, reset_activities):
        """Test multiple different students can signup"""
        # Arrange
        activity_name = "Art Studio"
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        initial_count = len(activities[activity_name]["participants"])

        # Act
        for email in emails:
            response = client.post(f"/activities/{activity_name}/signup?email={email}")
            assert response.status_code == 200

        # Assert
        participants = activities[activity_name]["participants"]
        assert len(participants) == initial_count + len(emails)
        for email in emails:
            assert email in participants

    def test_signup_different_activities(self, client, reset_activities):
        """Test student can signup for multiple activities"""
        # Arrange
        email = "versatile@mergington.edu"
        activities_to_join = ["Chess Club", "Drama Club", "Science Club"]

        # Act
        for activity in activities_to_join:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200

        # Assert
        for activity in activities_to_join:
            assert email in activities[activity]["participants"]

    def test_signup_respects_max_participants(self, client, reset_activities):
        """Test that signup works when activity is not full"""
        # Arrange
        activity_name = "Tennis Club"
        email = "newtennis@mergington.edu"
        initial_count = len(activities[activity_name]["participants"])

        # Act
        response = client.post(f"/activities/{activity_name}/signup?email={email}")

        # Assert
        assert response.status_code == 200
        assert len(activities[activity_name]["participants"]) == initial_count + 1
        assert email in activities[activity_name]["participants"]


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/participants/{email} endpoint"""

    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration from activity"""
        # Arrange
        activity_name = "Chess Club"
        email = "michael@mergington.edu"
        assert email in activities[activity_name]["participants"]
        initial_count = len(activities[activity_name]["participants"])

        # Act
        response = client.delete(f"/activities/{activity_name}/participants/{email}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert email not in activities[activity_name]["participants"]
        assert len(activities[activity_name]["participants"]) == initial_count - 1

    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregister fails for non-existent activity"""
        # Arrange
        activity_name = "Nonexistent Activity"
        email = "student@mergington.edu"

        # Act
        response = client.delete(f"/activities/{activity_name}/participants/{email}")

        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_not_registered_student(self, client, reset_activities):
        """Test unregister fails for student not in activity"""
        # Arrange
        activity_name = "Chess Club"
        email = "notstudent@mergington.edu"

        # Act
        response = client.delete(f"/activities/{activity_name}/participants/{email}")

        # Assert
        assert response.status_code == 404
        assert "not signed up" in response.json()["detail"]

    def test_unregister_multiple_students(self, client, reset_activities):
        """Test unregistering multiple students"""
        # Arrange
        activity_name = "Debate Team"
        emails = ["temp1@mergington.edu", "temp2@mergington.edu", "temp3@mergington.edu"]

        # First add students
        for email in emails:
            client.post(f"/activities/{activity_name}/signup?email={email}")
            assert email in activities[activity_name]["participants"]

        # Act - Remove them
        for email in emails:
            response = client.delete(f"/activities/{activity_name}/participants/{email}")
            assert response.status_code == 200

        # Assert
        for email in emails:
            assert email not in activities[activity_name]["participants"]

    def test_signup_after_unregister(self, client, reset_activities):
        """Test student can re-register after unregistering"""
        # Arrange
        activity_name = "Drama Club"
        email = "flaky@mergington.edu"

        # Act - Sign up
        client.post(f"/activities/{activity_name}/signup?email={email}")
        assert email in activities[activity_name]["participants"]

        # Act - Unregister
        client.delete(f"/activities/{activity_name}/participants/{email}")
        assert email not in activities[activity_name]["participants"]

        # Act - Sign up again
        response = client.post(f"/activities/{activity_name}/signup?email={email}")

        # Assert
        assert response.status_code == 200
        assert email in activities[activity_name]["participants"]


class TestIntegrationScenarios:
    """Integration tests for complex scenarios"""

    def test_full_activity_lifecycle(self, client, reset_activities):
        """Test complete lifecycle: view activities, signup, view, unregister"""
        # Arrange
        activity_name = "Programming Class"
        email = "lifecycle@mergington.edu"

        # Act - Get initial state
        response = client.get("/activities")
        initial_count = len(response.json()[activity_name]["participants"])

        # Act - Sign up
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert response.status_code == 200

        # Act - Verify signup via GET
        response = client.get("/activities")
        signup_data = response.json()

        # Assert - Signup verification
        assert len(signup_data[activity_name]["participants"]) == initial_count + 1
        assert email in signup_data[activity_name]["participants"]

        # Act - Unregister
        response = client.delete(f"/activities/{activity_name}/participants/{email}")
        assert response.status_code == 200

        # Act - Verify unregister via GET
        response = client.get("/activities")
        final_data = response.json()

        # Assert - Unregister verification
        assert len(final_data[activity_name]["participants"]) == initial_count
        assert email not in final_data[activity_name]["participants"]

    def test_concurrent_signups(self, client, reset_activities):
        """Test multiple students signup for same activity"""
        # Arrange
        activity_name = "Gym Class"
        initial_count = len(activities[activity_name]["participants"])
        emails = [f"student{i}@mergington.edu" for i in range(5)]

        # Act
        for email in emails:
            response = client.post(f"/activities/{activity_name}/signup?email={email}")
            assert response.status_code == 200

        # Assert
        assert len(activities[activity_name]["participants"]) == initial_count + len(emails)
        for email in emails:
            assert email in activities[activity_name]["participants"]