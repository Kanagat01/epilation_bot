"""full_name divided to first_name and last_name

Revision ID: 8c540cfc6fb4
Revises: dc31857ae058
Create Date: 2024-01-03 17:24:23.789506

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8c540cfc6fb4'
down_revision = 'dc31857ae058'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('clients', sa.Column('first_name', sa.String(), nullable=False))
    op.add_column('clients', sa.Column('last_name', sa.String(), nullable=False))
    op.drop_column('clients', 'full_name')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('clients', sa.Column('full_name', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.drop_column('clients', 'last_name')
    op.drop_column('clients', 'first_name')
    # ### end Alembic commands ###
