"""Initial schema."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260325_0001"
down_revision = None
branch_labels = None
depends_on = None


watchlist_status = sa.Enum("active", "paused", name="watchliststatus", native_enum=False, length=20)
notification_status = sa.Enum("pending", "sent", "failed", name="notificationstatus", native_enum=False, length=20)
sync_status = sa.Enum("running", "success", "failed", name="syncrunstatus", native_enum=False, length=20)


def upgrade() -> None:
    op.create_table(
        "fuels",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("dataset_key", sa.String(length=150), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_fuels_code", "fuels", ["code"], unique=True)
    op.create_index("ix_fuels_dataset_key", "fuels", ["dataset_key"], unique=True)

    op.create_table(
        "stations",
        sa.Column("ideess", sa.String(length=16), primary_key=True),
        sa.Column("postal_code", sa.String(length=10)),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("address_normalized", sa.String(length=255), nullable=False),
        sa.Column("locality", sa.String(length=255)),
        sa.Column("locality_normalized", sa.String(length=255)),
        sa.Column("municipality", sa.String(length=255), nullable=False),
        sa.Column("municipality_normalized", sa.String(length=255), nullable=False),
        sa.Column("province", sa.String(length=255), nullable=False),
        sa.Column("province_normalized", sa.String(length=255), nullable=False),
        sa.Column("brand", sa.String(length=255), nullable=False),
        sa.Column("brand_normalized", sa.String(length=255), nullable=False),
        sa.Column("schedule", sa.Text()),
        sa.Column("margin", sa.String(length=50)),
        sa.Column("sale_type", sa.String(length=50)),
        sa.Column("remision", sa.String(length=100)),
        sa.Column("locality_code", sa.String(length=10)),
        sa.Column("province_code", sa.String(length=10)),
        sa.Column("autonomous_region_code", sa.String(length=10)),
        sa.Column("latitude", sa.Numeric(10, 7)),
        sa.Column("longitude", sa.Numeric(10, 7)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_stations_postal_code", "stations", ["postal_code"])
    op.create_index("ix_stations_municipality", "stations", ["municipality_normalized"])
    op.create_index("ix_stations_province", "stations", ["province_normalized"])
    op.create_index("ix_stations_brand", "stations", ["brand_normalized"])
    op.create_index("ix_stations_locality", "stations", ["locality_normalized"])
    op.create_index("ix_stations_address", "stations", ["address_normalized"])
    op.execute(
        "CREATE FULLTEXT INDEX ft_stations_search ON stations "
        "(brand, address, municipality, locality)"
    )

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255)),
        sa.Column("first_name", sa.String(length=255)),
        sa.Column("last_name", sa.String(length=255)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_telegram_user_id", "users", ["telegram_user_id"], unique=True)
    op.create_index("ix_users_username", "users", ["username"])

    op.create_table(
        "sync_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("status", sync_status, nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("dataset_timestamp", sa.DateTime(timezone=True)),
        sa.Column("stations_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("price_rows_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("price_rows_changed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("price_drops_detected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text()),
    )
    op.create_index("ix_sync_runs_status", "sync_runs", ["status"])
    op.create_index("ix_sync_runs_dataset_timestamp", "sync_runs", ["dataset_timestamp"])

    op.create_table(
        "station_prices_current",
        sa.Column("station_id", sa.String(length=16), sa.ForeignKey("stations.ideess", ondelete="CASCADE"), primary_key=True),
        sa.Column("fuel_id", sa.Integer(), sa.ForeignKey("fuels.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("current_price", sa.Numeric(10, 3), nullable=False),
        sa.Column("dataset_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_station_prices_current_station_fuel", "station_prices_current", ["station_id", "fuel_id"], unique=True)
    op.create_index("ix_station_prices_current_price", "station_prices_current", ["current_price"])

    op.create_table(
        "station_price_history",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("station_id", sa.String(length=16), sa.ForeignKey("stations.ideess", ondelete="CASCADE"), nullable=False),
        sa.Column("fuel_id", sa.Integer(), sa.ForeignKey("fuels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sync_run_id", sa.BigInteger(), sa.ForeignKey("sync_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_price", sa.Numeric(10, 3)),
        sa.Column("new_price", sa.Numeric(10, 3), nullable=False),
        sa.Column("dataset_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("station_id", "fuel_id", "sync_run_id", name="uq_station_price_history_sync"),
    )
    op.create_index("ix_station_price_history_station_fuel", "station_price_history", ["station_id", "fuel_id"])

    op.create_table(
        "user_watchlists",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("station_id", sa.String(length=16), sa.ForeignKey("stations.ideess", ondelete="CASCADE"), nullable=False),
        sa.Column("fuel_id", sa.Integer(), sa.ForeignKey("fuels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", watchlist_status, nullable=False, server_default="active"),
        sa.Column("last_notified_price", sa.Numeric(10, 3)),
        sa.Column("last_notification_at", sa.DateTime(timezone=True)),
        sa.Column("paused_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "station_id", "fuel_id", name="uq_user_watchlists_target"),
    )
    op.create_index("ix_user_watchlists_status", "user_watchlists", ["status"])
    op.create_index("ix_user_watchlists_station_fuel", "user_watchlists", ["station_id", "fuel_id"])

    op.create_table(
        "notifications_sent",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("watchlist_id", sa.BigInteger(), sa.ForeignKey("user_watchlists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sync_run_id", sa.BigInteger(), sa.ForeignKey("sync_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("station_id", sa.String(length=16), sa.ForeignKey("stations.ideess", ondelete="CASCADE"), nullable=False),
        sa.Column("fuel_id", sa.Integer(), sa.ForeignKey("fuels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_price", sa.Numeric(10, 3), nullable=False),
        sa.Column("new_price", sa.Numeric(10, 3), nullable=False),
        sa.Column("dataset_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", notification_status, nullable=False, server_default="pending"),
        sa.Column("telegram_message_id", sa.Integer()),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text()),
        sa.UniqueConstraint("watchlist_id", "sync_run_id", name="uq_notifications_sent_watchlist_sync"),
    )
    op.create_index("ix_notifications_sent_status", "notifications_sent", ["status"])
    op.create_index("ix_notifications_sent_station_fuel", "notifications_sent", ["station_id", "fuel_id"])

    op.bulk_insert(
        sa.table(
            "fuels",
            sa.column("id", sa.Integer()),
            sa.column("code", sa.String()),
            sa.column("name", sa.String()),
            sa.column("dataset_key", sa.String()),
            sa.column("display_order", sa.Integer()),
            sa.column("is_active", sa.Boolean()),
        ),
        [
            {"id": 1, "code": "gasoleo_a", "name": "Gasoleo A", "dataset_key": "Precio_x0020_Gasoleo_x0020_A", "display_order": 10, "is_active": True},
            {"id": 2, "code": "gasoleo_premium", "name": "Gasoleo Premium", "dataset_key": "Precio_x0020_Gasoleo_x0020_Premium", "display_order": 20, "is_active": True},
            {"id": 3, "code": "gasoleo_b", "name": "Gasoleo B", "dataset_key": "Precio_x0020_Gasoleo_x0020_B", "display_order": 30, "is_active": True},
            {"id": 4, "code": "gasolina_95_e5", "name": "Gasolina 95 E5", "dataset_key": "Precio_x0020_Gasolina_x0020_95_x0020_E5", "display_order": 40, "is_active": True},
            {"id": 5, "code": "gasolina_95_premium", "name": "Gasolina 95 E5 Premium", "dataset_key": "Precio_x0020_Gasolina_x0020_95_x0020_E5_x0020_Premium", "display_order": 50, "is_active": True},
            {"id": 6, "code": "gasolina_98_e5", "name": "Gasolina 98 E5", "dataset_key": "Precio_x0020_Gasolina_x0020_98_x0020_E5", "display_order": 60, "is_active": True},
            {"id": 7, "code": "gasolina_95_e10", "name": "Gasolina 95 E10", "dataset_key": "Precio_x0020_Gasolina_x0020_95_x0020_E10", "display_order": 70, "is_active": True},
            {"id": 8, "code": "gasolina_98_e10", "name": "Gasolina 98 E10", "dataset_key": "Precio_x0020_Gasolina_x0020_98_x0020_E10", "display_order": 80, "is_active": True},
            {"id": 9, "code": "glp", "name": "GLP", "dataset_key": "Precio_x0020_Gases_x0020_licuados_x0020_del_x0020_petr\u00f3leo", "display_order": 90, "is_active": True},
            {"id": 10, "code": "gnc", "name": "GNC", "dataset_key": "Precio_x0020_Gas_x0020_Natural_x0020_Comprimido", "display_order": 100, "is_active": True},
            {"id": 11, "code": "gnl", "name": "GNL", "dataset_key": "Precio_x0020_Gas_x0020_Natural_x0020_Licuado", "display_order": 110, "is_active": True},
            {"id": 12, "code": "adblue", "name": "AdBlue", "dataset_key": "Precio_x0020_Adblue", "display_order": 120, "is_active": True},
            {"id": 13, "code": "diesel_renovable", "name": "Diesel Renovable", "dataset_key": "Precio_x0020_Di\u00e9sel_x0020_Renovable", "display_order": 130, "is_active": True},
            {"id": 14, "code": "gasolina_renovable", "name": "Gasolina Renovable", "dataset_key": "Precio_x0020_Gasolina_x0020_Renovable", "display_order": 140, "is_active": True},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_sent_station_fuel", table_name="notifications_sent")
    op.drop_index("ix_notifications_sent_status", table_name="notifications_sent")
    op.drop_table("notifications_sent")

    op.drop_index("ix_user_watchlists_station_fuel", table_name="user_watchlists")
    op.drop_index("ix_user_watchlists_status", table_name="user_watchlists")
    op.drop_table("user_watchlists")

    op.drop_index("ix_station_price_history_station_fuel", table_name="station_price_history")
    op.drop_table("station_price_history")

    op.drop_index("ix_station_prices_current_price", table_name="station_prices_current")
    op.drop_index("ix_station_prices_current_station_fuel", table_name="station_prices_current")
    op.drop_table("station_prices_current")

    op.drop_index("ix_sync_runs_dataset_timestamp", table_name="sync_runs")
    op.drop_index("ix_sync_runs_status", table_name="sync_runs")
    op.drop_table("sync_runs")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_telegram_user_id", table_name="users")
    op.drop_table("users")

    op.execute("DROP INDEX ft_stations_search ON stations")
    op.drop_index("ix_stations_address", table_name="stations")
    op.drop_index("ix_stations_locality", table_name="stations")
    op.drop_index("ix_stations_brand", table_name="stations")
    op.drop_index("ix_stations_province", table_name="stations")
    op.drop_index("ix_stations_municipality", table_name="stations")
    op.drop_index("ix_stations_postal_code", table_name="stations")
    op.drop_table("stations")

    op.drop_index("ix_fuels_dataset_key", table_name="fuels")
    op.drop_index("ix_fuels_code", table_name="fuels")
    op.drop_table("fuels")
