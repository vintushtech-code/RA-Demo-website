import sqlite3
import logging
from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class LoginConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'login'
    verbose_name = 'Standalone Authentication & User Management'

    def ready(self):
        """
        Auto-applies schema migrations for ConsultationBooking, SaaS Subscriptions, and Backup logs.
        Connects model signals for continuous automated database backups.
        """
        try:
            db_path = settings.BASE_DIR / 'db.sqlite3'
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                
                # 1. ConsultationBooking dynamic billing & pricing fields
                cursor.execute("PRAGMA table_info(login_consultationbooking)")
                existing_cols = [row[1] for row in cursor.fetchall()]
                if existing_cols:
                    columns_to_add = [
                        ("fee_amount", "decimal DEFAULT 5000.0"),
                        ("discount_amount", "decimal DEFAULT 0.0"),
                        ("net_amount", "decimal DEFAULT 5000.0"),
                        ("invoice_number", "varchar(50) DEFAULT ''"),
                        ("payment_method", "varchar(50) DEFAULT 'UPI / Net Banking / Card'"),
                        ("transaction_id", "varchar(100) DEFAULT ''"),
                        ("fiduciary_desk", "varchar(150) DEFAULT 'Senior Wealth Advisory & Fiduciary Desk'"),
                        ("meeting_link", "varchar(500) DEFAULT ''"),
                        ("client_instructions", "text DEFAULT ''"),
                    ]
                    for col_name, col_type in columns_to_add:
                        if col_name not in existing_cols:
                            cursor.execute(f"ALTER TABLE login_consultationbooking ADD COLUMN {col_name} {col_type}")

                # 2. SaaS Subscription Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS login_adminsaassubscription (
                        id integer PRIMARY KEY AUTOINCREMENT,
                        service_name varchar(200) NOT NULL,
                        client_name varchar(200) NOT NULL,
                        client_email varchar(254) NOT NULL,
                        provider_credits varchar(255) NOT NULL,
                        is_free_trial bool NOT NULL,
                        trial_start_date datetime NOT NULL,
                        trial_duration_days integer NOT NULL,
                        trial_end_date datetime,
                        subscription_status varchar(50) NOT NULL,
                        current_plan varchar(50) NOT NULL,
                        paid_until datetime,
                        license_key varchar(150) NOT NULL,
                        is_locked bool NOT NULL,
                        notes text NOT NULL,
                        created_at datetime NOT NULL,
                        updated_at datetime NOT NULL
                    )
                """)

                # 3. Backup Log Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS login_adminbackuplog (
                        id integer PRIMARY KEY AUTOINCREMENT,
                        file_name varchar(255) NOT NULL,
                        file_path varchar(500) NOT NULL,
                        file_size_kb real NOT NULL,
                        trigger_event varchar(255) NOT NULL,
                        is_automated bool NOT NULL,
                        status varchar(50) NOT NULL,
                        created_at datetime NOT NULL
                    )
                """)

                # 4. Seed initial 3-month free trial if not present
                cursor.execute("SELECT COUNT(*) FROM login_adminsaassubscription")
                count = cursor.fetchone()[0]
                if count == 0:
                    import datetime
                    now_dt = datetime.datetime.now()
                    end_dt = now_dt + datetime.timedelta(days=90)
                    now_str = now_dt.strftime('%Y-%m-%d %H:%M:%S')
                    end_str = end_dt.strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute("""
                        INSERT INTO login_adminsaassubscription (
                            service_name, client_name, client_email, provider_credits,
                            is_free_trial, trial_start_date, trial_duration_days, trial_end_date,
                            subscription_status, current_plan, paid_until, license_key, is_locked,
                            notes, created_at, updated_at
                        ) VALUES (
                            'GuardianTree FP Executive Admin Panel',
                            'Sabin Balan (Founder, GuardianTree FP)',
                            'sabin@guardiantreefp.com',
                            'VintushTech & KPRegTech',
                            1, ?, 90, ?,
                            'active_trial', 'trial_3_months', ?, 'KP-VINTUSH-3M-TRIAL-ACTIVE', 0,
                            'Initial 3-month complimentary trial granted by VintushTech & KPRegTech.',
                            ?, ?
                        )
                    """, (now_str, end_str, end_str, now_str, now_str))

                conn.commit()
                conn.close()
        except Exception as e:
            logger.warning("[LoginConfig] Auto-migration check: %s", e)

        # Connect continuous backup signal to admin model modifications
        try:
            import sys
            # Only connect live backup signal when not running migrations or automated tests
            is_testing_or_migrating = any(cmd in sys.argv for cmd in ['test', 'migrate', 'makemigrations', 'collectstatic'])
            
            if not is_testing_or_migrating:
                from django.db.models.signals import post_save, post_delete
                from .backup_service import create_live_backup

                def auto_backup_handler(sender, **kwargs):
                    # Avoid infinite recursion or raw data loads
                    if kwargs.get('raw', False) or sender.__name__ in ['AdminBackupLog', 'Session', 'LogEntry', 'Migration']:
                        return
                    try:
                        create_live_backup(event_trigger=f"Model Saved/Deleted: {sender.__name__}")
                    except Exception:
                        pass

                post_save.connect(auto_backup_handler, dispatch_uid="saas_auto_backup_post_save")
                post_delete.connect(auto_backup_handler, dispatch_uid="saas_auto_backup_post_delete")
        except Exception as e:
            logger.warning("[LoginConfig] Signal setup error: %s", e)

