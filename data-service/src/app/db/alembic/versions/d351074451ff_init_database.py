"""Init database

Revision ID: d351074451ff
Revises:
Create Date: 2025-11-04 18:30:30.276069

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd351074451ff'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('products',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('flow_type', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('phone', sa.String(), nullable=False),
    sa.Column('age', sa.Integer(), nullable=False),
    sa.Column('monthly_income', sa.Integer(), nullable=False),
    sa.Column('employment_type', sa.String(), nullable=False),
    sa.Column('has_property', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('loans',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('loan_id', sa.String(), nullable=False),
    sa.Column('product_name', sa.String(), nullable=False),
    sa.Column('amount', sa.Integer(), nullable=False),
    sa.Column('issue_date', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('term_days', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('close_date', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('profile_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('loan_id')
    )
    op.bulk_insert(sa.table('products',
                   sa.column('id'), sa.column('name'), sa.column('flow_type')),
                   [
                       {'id': 1, 'name': 'ConsumerLoan', 'flow_type': 'pioneer'},
                       {'id': 2, 'name': 'QuickMoney', 'flow_type': 'pioneer'},
                       {'id': 3, 'name': 'MicroLoan', 'flow_type': 'pioneer'},
                       {'id': 4, 'name': 'PrimeCredit', 'flow_type': 'repeater'},
                       {'id': 5, 'name': 'AdvantagePlus', 'flow_type': 'repeater'},
                       {'id': 6, 'name': 'LoyaltyLoan', 'flow_type': 'repeater'}
                   ]
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('loans')
    op.drop_table('users')
    op.drop_table('products')
    # ### end Alembic commands ###
