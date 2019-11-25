def test_benchmark_insert(benchmark, user_model, users_data):
    def do_insert():
        return user_model.insert(**users_data[0]).execute()

    user = benchmark(do_insert)
    user_cache = user_model.get(id=user.id)
    assert user == user_cache


def test_benchmark_insert_many(benchmark, user_model, users_data):
    def do_insert_many():
        return user_model.insert_many(*users_data).execute()

    users = benchmark(do_insert_many)
    for user in users:
        assert user == user_model.get(id=user.id)


def test_benchmark_query(benchmark, user_model, users_data):
    def do_query(**query):
        return user_model.query(**query).execute()

    user = user_model.insert(**users_data[0]).execute()
    got_user = benchmark(do_query, id=user.id)
    assert user == got_user


def test_benchmark_query_many(benchmark, user_model, users_data):
    def do_query_many(query_list):
        return user_model.query_many(*query_list).execute()

    users = user_model.insert_many(*users_data).execute()
    got_users = benchmark(do_query_many, [{"id": u.id} for u in users])
    assert users == got_users


def test_benchmark_update(benchmark, user_model, users_data):
    def do_update(**update):
        return user_model.update(**update).execute()

    user = user_model.insert(**users_data[0]).execute()
    got_user = benchmark(do_update, id=user.id, married=True)
    assert user_model.get(id=user.id).married == got_user.married


def test_benchmark_update_many(benchmark, user_model, users_data):
    def do_update_many(update_list):
        return user_model.update_many(*update_list).execute()

    users = user_model.insert_many(*users_data).execute()
    got_users = benchmark(
        do_update_many, [{"id": u.id, "married": True} for u in users]
    )
    for user in got_users:
        assert user.married is True


def test_benchmark_delete(benchmark, user_model, users_data):
    def do_delete(**delete):
        user_model.delete(**delete).execute()

    user = user_model.insert(**users_data[0]).execute()
    benchmark(do_delete, id=user.id)
    assert user_model.get_or_none(id=user.id) is None


def test_benchmark_delete_many(benchmark, user_model, users_data):
    def do_delete_many(delete_list):
        user_model.delete_many(*delete_list).execute()

    users = user_model.insert_many(*users_data).execute()
    benchmark(do_delete_many, [{"id": u.id} for u in users])
    for u in users:
        assert user_model.get_or_none(id=u.id) is None
