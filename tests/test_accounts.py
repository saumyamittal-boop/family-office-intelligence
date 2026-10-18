import pytest

from fo import accounts, engine
from fo.data import make_sample_returns
from fo.personas import PERSONAS, profile_from_dict, profile_to_dict, starter_profile


@pytest.fixture()
def db(tmp_path):
    path = tmp_path / "test.db"
    accounts.init_db(path)
    return path


def test_create_and_authenticate(db):
    user = accounts.create_user("Priya_Family", "correct horse battery", db)
    assert user["username"] == "Priya_Family"
    assert accounts.authenticate("Priya_Family", "correct horse battery", db)["id"] == user["id"]
    assert accounts.authenticate("priya_family", "correct horse battery", db) is not None  # usernames ignore case
    assert accounts.authenticate("Priya_Family", "wrong password!!", db) is None
    assert accounts.authenticate("nobody", "correct horse battery", db) is None


def test_passwords_are_hashed_not_stored(db):
    accounts.create_user("hash_check", "plain-text-secret", db)
    with accounts._db(db) as con:
        row = con.execute("SELECT salt, hash FROM users WHERE username = 'hash_check'").fetchone()
    assert b"plain-text-secret" not in bytes(row["hash"]) + bytes(row["salt"])
    assert len(row["hash"]) == 32 and len(row["salt"]) == 16


def test_username_and_password_rules(db):
    with pytest.raises(ValueError, match="Username"):
        accounts.create_user("ab", "long enough pw", db)
    with pytest.raises(ValueError, match="Username"):
        accounts.create_user("has space", "long enough pw", db)
    with pytest.raises(ValueError, match="Password"):
        accounts.create_user("valid_name", "short", db)
    accounts.create_user("taken_name", "long enough pw", db)
    with pytest.raises(ValueError, match="already taken"):
        accounts.create_user("TAKEN_NAME", "another long pw", db)


def test_demo_accounts_exist_but_have_no_password_login(db):
    for username in accounts.DEMO_ACCOUNTS:
        demo = accounts.demo_user(username, db)
        assert demo and demo["is_demo"]
        assert accounts.authenticate(username, "", db) is None
        assert accounts.authenticate(username, "password", db) is None
    assert accounts.demo_user("not_a_demo", db) is None
    # re-running init does not duplicate them
    accounts.init_db(db)
    assert len(accounts.list_profiles(accounts.demo_user("legacy", db)["id"], db)) == 1


def test_each_user_only_sees_their_own_profiles(db):
    alice = accounts.create_user("alice_fo", "alice password 1", db)
    bob = accounts.create_user("bob_fo", "bob password 123", db)
    alice_profile_id = accounts.list_profiles(alice["id"], db)[0][0]
    bob_profile_id = accounts.list_profiles(bob["id"], db)[0][0]
    assert alice_profile_id != bob_profile_id

    assert accounts.get_profile(bob["id"], alice_profile_id, db) is None  # cannot read another's profile
    changed = starter_profile("hijacked")
    assert accounts.save_profile(bob["id"], alice_profile_id, changed, db) is False  # cannot overwrite it
    assert accounts.get_profile(alice["id"], alice_profile_id, db).name != "hijacked"
    assert accounts.delete_profile(bob["id"], alice_profile_id, db) is False  # cannot delete it
    assert accounts.get_profile(alice["id"], alice_profile_id, db) is not None


def test_add_save_and_delete_profiles_but_never_the_last(db):
    user = accounts.create_user("saver_fo", "saver password 1", db)
    first_id = accounts.list_profiles(user["id"], db)[0][0]
    assert accounts.delete_profile(user["id"], first_id, db) is False  # only profile

    second_id = accounts.add_profile(user["id"], starter_profile("Second plan"), db)
    assert len(accounts.list_profiles(user["id"], db)) == 2
    edited = profile_from_dict({**profile_to_dict(starter_profile("Second plan")), "corpus_cr": 321.0, "name": "Renamed"})
    assert accounts.save_profile(user["id"], second_id, edited, db) is True
    stored = accounts.get_profile(user["id"], second_id, db)
    assert stored.name == "Renamed" and stored.corpus_cr == 321.0

    assert accounts.delete_profile(user["id"], second_id, db) is True
    assert len(accounts.list_profiles(user["id"], db)) == 1


@pytest.mark.parametrize("key", ["A", "B", "C"])
def test_profile_serialisation_round_trip(key):
    original = PERSONAS[key]
    restored = profile_from_dict(profile_to_dict(original), key=original.key)
    assert restored == original


def test_a_brand_new_accounts_starter_profile_can_be_analysed(db):
    user = accounts.create_user("fresh_fo", "fresh password 1", db)
    profile = accounts.list_profiles(user["id"], db)[0][1]
    daily = make_sample_returns()
    portfolios = engine.recommend(profile, daily)
    assert len(portfolios) == 3
    assert engine.analyse_current(profile, daily).weights_sleeve.sum() == pytest.approx(1.0)
