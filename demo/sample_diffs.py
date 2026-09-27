"""Synthetic PR diffs for demo purposes.

These diffs simulate a PR that violates several team conventions,
allowing the demo to show how memory-augmented reviews differ
from generic reviews.
"""

from core.models import PRInfo, FileDiff


def get_demo_pr_info() -> PRInfo:
    """Get synthetic PR metadata."""
    return PRInfo(
        url="https://github.com/kaushikteja26/code_review_agent/pull/2",
        owner="kaushikteja26",
        repo="code_review_agent",
        number=2,
        title="Add user profile endpoint and notification service",
        author="junior-dev",
        description="Added new endpoint for user profiles and integrated notification service.",
        base_branch="main",
        head_branch="feature/user-profiles",
    )


def get_demo_files() -> list[FileDiff]:
    """Get synthetic file diffs that deliberately violate team conventions."""
    return [
        FileDiff(
            filename="app/routes/users.py",
            status="added",
            additions=45,
            deletions=0,
            patch='''@@ -0,0 +1,45 @@
+from fastapi import APIRouter, HTTPException
+import sqlite3
+import requests
+
+router = APIRouter()
+
+@router.get("/users/{user_id}")
+def get_user_profile(user_id: int):
+    """Get user profile by ID."""
+    conn = sqlite3.connect("app.db")
+    cursor = conn.cursor()
+    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
+    user = cursor.fetchone()
+    conn.close()
+    
+    if not user:
+        raise HTTPException(status_code=404, detail="User not found")
+    
+    return {"id": user[0], "name": user[1], "email": user[2]}
+
+
+@router.post("/users/{user_id}/notify")
+def send_notification(user_id: int, message: str):
+    """Send notification to user."""
+    conn = sqlite3.connect("app.db")
+    cursor = conn.cursor()
+    cursor.execute(f"SELECT email FROM users WHERE id = {user_id}")
+    user = cursor.fetchone()
+    conn.close()
+    
+    if not user:
+        raise HTTPException(status_code=404, detail="User not found")
+    
+    # Call external notification service synchronously
+    response = requests.post(
+        "https://notify.example.com/send",
+        json={"email": user[0], "message": message}
+    )
+    
+    if response.status_code != 200:
+        return {"error": "Failed to send notification", "status": response.status_code}
+    
+    return {"status": "sent", "email": user[0]}
+
+
+@router.delete("/users/{user_id}")
+def delete_user(user_id: int):
+    conn = sqlite3.connect("app.db")
+    conn.execute(f"DELETE FROM users WHERE id = {user_id}")
+    conn.commit()
+    conn.close()
+    return {"deleted": True}''',
        ),
        FileDiff(
            filename="app/routes/orders.py",
            status="modified",
            additions=22,
            deletions=3,
            patch='''@@ -15,8 +15,27 @@
+from datetime import datetime
+import psycopg2
+import json
+
 @router.get("/orders/{order_id}")
-async def get_order(order_id: int):
-    return await order_service.get(order_id)
+def get_order(order_id: int):
+    """Get order details."""
+    conn = psycopg2.connect("dbname=orders user=admin password=secret123")
+    cursor = conn.cursor()
+    cursor.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
+    order = cursor.fetchone()
+    conn.close()
+    
+    if not order:
+        return {"error": "Order not found"}, 404
+    
+    return {"id": order[0], "total": float(order[3]), "status": order[4]}
+
+
+@router.post("/orders")
+def create_order(data: dict):
+    """Create a new order."""
+    conn = psycopg2.connect("dbname=orders user=admin password=secret123")
+    cursor = conn.cursor()
+    cursor.execute(
+        f"INSERT INTO orders (user_id, items, total, status) VALUES ({data['user_id']}, '{json.dumps(data['items'])}', {data['total']}, 'pending')"
+    )
+    conn.commit()
+    conn.close()
+    return {"status": "created"}''',
        ),
        FileDiff(
            filename="app/utils/validator.py",
            status="added",
            additions=12,
            deletions=0,
            patch='''@@ -0,0 +1,12 @@
+def validate_email(email):
+    if "@" in email:
+        return True
+    return False
+
+def validate_user_data(data):
+    if not data.get("name"):
+        return False
+    if not data.get("email"):
+        return False
+    if not validate_email(data["email"]):
+        return False
+    return True''',
        ),
    ]
