# A secret *reference* — a name/path, never a value — must NOT be flagged. This is
# exactly the shape QMF components are built to carry (SecretRef).
from qmf.core.secret import SecretRef

db_password_ref = SecretRef.try_create(store="vault", path="prod/db/password")
api_token_ref = SecretRef.try_create(store="env", path="SLACK_BOT_TOKEN")
