def handle(self, *args, **options):
    base_dir = settings.BASE_DIR
    sql_file_path = os.path.join(base_dir, 'exported_sql', 'swimlings.sql')

    if not os.path.exists(sql_file_path):
        self.stderr.write(self.style.ERROR(f"❌ SQL file not found: {sql_file_path}"))
        return

    # Get DB credentials
    db = settings.DATABASES['default']
    user = db['USER']
    password = db['PASSWORD']
    host = db['HOST']
    name = db['NAME']

    self.stdout.write(self.style.WARNING(f"📥 Importing {sql_file_path} into `{name}` with FK checks disabled..."))

    try:
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        full_sql = f"""
        SET FOREIGN_KEY_CHECKS=0;
        TRUNCATE TABLE waiting_list_waitinglist;
        TRUNCATE TABLE schools_orders_orderitem;
        TRUNCATE TABLE users_swimling;
        {sql_content}
        SET FOREIGN_KEY_CHECKS=1;
        """

        subprocess.run(
            ['mysql', f'-u{user}', f'-p{password}', f'-h{host}', name],
            input=full_sql.encode('utf-8'),
            check=True
        )
        self.stdout.write(self.style.SUCCESS("✅ Swimlings import completed with IDs preserved."))

    except subprocess.CalledProcessError as e:
        self.stderr.write(self.style.ERROR(f"❌ MySQL import failed: {e}"))
