"""Legacy Flutter API contract tests using an isolated in-memory database."""
import os
import unittest

os.environ.setdefault("JWT_SECRET_KEY", "legacy-recovery-test-secret-at-least-32-bytes")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import password_hasher
from app.db.database import get_db
from app.db.models import Base, ChatRoom, ChatRoomMember, Friendship, Message, User
from app.main import app


class ApiContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.testing_session = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
        )
        Base.metadata.create_all(self.engine)

        with self.testing_session() as db:
            owner = User(
                login_id="halmeoni",
                password_hash=password_hasher.hash("test1234"),
                name="김순자",
                profile_image="/static/users/user1.jpg",
                introduce="안녕하세요.",
            )
            friend = User(
                login_id="friend01",
                password_hash=password_hasher.hash("test1234"),
                name="이영희",
                profile_image="/static/users/user2.jpg",
                introduce="딸입니다.",
            )
            db.add_all([owner, friend])
            db.flush()
            db.add(Friendship(user_id=owner.id, friend_id=friend.id))
            room = ChatRoom()
            db.add(room)
            db.flush()
            db.add_all(
                [
                    ChatRoomMember(chat_room_id=room.id, user_id=owner.id),
                    ChatRoomMember(chat_room_id=room.id, user_id=friend.id),
                    Message(
                        chat_room_id=room.id,
                        sender_id=friend.id,
                        content="검찰입니다. 현금을 인출해 지정 장소로 가져오세요.",
                    ),
                ]
            )
            db.commit()

        def override_get_db():
            db = self.testing_session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()

    def login(self) -> tuple[dict, dict[str, str]]:
        response = self.client.post(
            "/api/v1/auth/login",
            json={"login_id": "halmeoni", "password": "test1234"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        token = body["data"]["access_token"]
        return body, {"Authorization": f"Bearer {token}"}

    def test_login_and_current_user_contract(self) -> None:
        body, headers = self.login()
        self.assertIs(body["success"], True)
        self.assertEqual(
            body["data"]["user"],
            {
                "id": 1,
                "login_id": "halmeoni",
                "name": "김순자",
                "profile_image": "/static/users/user1.jpg",
            },
        )
        self.assertEqual(body["data"]["token_type"], "bearer")
        self.assertTrue(body["data"]["access_token"])

        me = self.client.get("/api/v1/users/me", headers=headers)
        self.assertEqual(me.status_code, 200, me.text)
        self.assertEqual(me.json()["data"]["user"]["login_id"], "halmeoni")

    def test_friends_chats_and_messages_contract(self) -> None:
        _, headers = self.login()

        friends = self.client.get("/api/v1/friends", headers=headers)
        self.assertEqual(friends.status_code, 200, friends.text)
        self.assertEqual(set(friends.json()), {"success", "data"})
        self.assertEqual(friends.json()["data"]["friends"][0]["login_id"], "friend01")

        chats = self.client.get("/api/v1/chats", headers=headers)
        self.assertEqual(chats.status_code, 200, chats.text)
        self.assertEqual(set(chats.json()["data"]), {"chats"})
        self.assertEqual(chats.json()["data"]["chats"][0]["friend"]["name"], "이영희")

        messages = self.client.get("/api/v1/chats/1/messages", headers=headers)
        self.assertEqual(messages.status_code, 200, messages.text)
        self.assertEqual(set(messages.json()["data"]), {"chat", "messages"})
        self.assertEqual(messages.json()["data"]["messages"][0]["sender_id"], 2)

        created = self.client.post(
            "/api/v1/chats/1/messages",
            headers=headers,
            json={"content": "확인했습니다."},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(set(created.json()["data"]), {"message"})
        self.assertEqual(created.json()["data"]["message"]["sender_id"], 1)

    def test_analysis_post_and_atm_use_the_same_session_id(self) -> None:
        _, headers = self.login()

        analyzed = self.client.post("/api/v1/analysis/chats/1", headers=headers)
        self.assertEqual(analyzed.status_code, 200, analyzed.text)
        data = analyzed.json()["data"]
        self.assertEqual(
            set(data),
            {
                "session_id",
                "analysis_id",
                "chat_id",
                "risk_level",
                "risk_score",
                "reasons",
                "summary",
                "analyzed_at",
            },
        )
        self.assertEqual(data["session_id"], f"VP-{data['analysis_id']:06d}")

        stored = self.client.get(f"/api/v1/analysis/{data['analysis_id']}", headers=headers)
        self.assertEqual(stored.status_code, 200, stored.text)
        self.assertEqual(stored.json()["data"]["analysis_id"], data["analysis_id"])

        atm = self.client.get(
            f"/api/v1/analysis/{data['analysis_id']}/atm",
            headers=headers,
        )
        self.assertEqual(atm.status_code, 200, atm.text)
        self.assertEqual(atm.json()["data"]["session_id"], data["session_id"])

        verified = self.client.get(f"/api/v1/atm/verify/{data['session_id']}")
        self.assertEqual(verified.status_code, 200, verified.text)
        self.assertEqual(verified.json()["data"]["session_id"], data["session_id"])


if __name__ == "__main__":
    unittest.main()
