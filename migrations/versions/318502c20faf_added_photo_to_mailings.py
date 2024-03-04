"""added photo to mailings

Revision ID: 318502c20faf
Revises: 001437340ae8
Create Date: 2024-03-04 18:27:27.565542

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '318502c20faf'
down_revision = '001437340ae8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('mailings', sa.Column('photo', sa.TEXT(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('mailings', 'photo')
    # ### end Alembic commands ###