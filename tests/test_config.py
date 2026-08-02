import pytest

from poke_track.config import load_config


def write_config(path, text):
    path.write_text(text)
    return str(path)


def test_loads_valid_config(tmp_path):
    config_path = write_config(
        tmp_path / "config.yaml",
        """
        poll_interval_seconds: 60
        products:
          - store: bestbuy
            url: "12345"
            name: "Test Item"
        """,
    )
    config = load_config(config_path, env_path=str(tmp_path / "does-not-exist.env"))
    assert config.poll_interval_seconds == 60
    assert len(config.products) == 1
    assert config.products[0].store == "bestbuy"
    assert config.products[0].name == "Test Item"


def test_defaults_poll_interval_when_omitted(tmp_path):
    config_path = write_config(
        tmp_path / "config.yaml",
        """
        products:
          - store: target
            url: "https://www.target.com/p/x/-/A-1"
        """,
    )
    config = load_config(config_path, env_path=str(tmp_path / "does-not-exist.env"))
    assert config.poll_interval_seconds == 300
    assert config.products[0].name == "https://www.target.com/p/x/-/A-1"


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(str(tmp_path / "nope.yaml"))


def test_unknown_store_raises(tmp_path):
    config_path = write_config(
        tmp_path / "config.yaml",
        """
        products:
          - store: walmart
            url: "https://www.walmart.com/ip/x/1"
        """,
    )
    with pytest.raises(ValueError, match="unknown store"):
        load_config(config_path, env_path=str(tmp_path / "does-not-exist.env"))


def test_missing_url_raises(tmp_path):
    config_path = write_config(
        tmp_path / "config.yaml",
        """
        products:
          - store: bestbuy
        """,
    )
    with pytest.raises(ValueError, match="needs either 'url' or 'search'"):
        load_config(config_path, env_path=str(tmp_path / "does-not-exist.env"))


def test_no_products_raises(tmp_path):
    config_path = write_config(tmp_path / "config.yaml", "products: []")
    with pytest.raises(ValueError, match="No products configured"):
        load_config(config_path, env_path=str(tmp_path / "does-not-exist.env"))


def test_loads_bestbuy_search_query(tmp_path):
    config_path = write_config(
        tmp_path / "config.yaml",
        """
        products:
          - store: bestbuy
            search: "Pokemon Trading Card Game"
            match_keywords:
              - "Elite Trainer Box"
              - "Booster Bundle"
            name: "Best Buy Pokemon TCG"
        """,
    )
    config = load_config(config_path, env_path=str(tmp_path / "does-not-exist.env"))
    assert config.products == []
    assert len(config.search_queries) == 1
    query = config.search_queries[0]
    assert query.store == "bestbuy"
    assert query.search == "Pokemon Trading Card Game"
    assert query.match_keywords == ["Elite Trainer Box", "Booster Bundle"]


def test_search_on_unsupported_store_raises(tmp_path):
    config_path = write_config(
        tmp_path / "config.yaml",
        """
        products:
          - store: target
            search: "pokemon"
        """,
    )
    with pytest.raises(ValueError, match="only supported for bestbuy"):
        load_config(config_path, env_path=str(tmp_path / "does-not-exist.env"))


def test_search_and_url_products_can_coexist(tmp_path):
    config_path = write_config(
        tmp_path / "config.yaml",
        """
        products:
          - store: bestbuy
            search: "pokemon"
          - store: target
            url: "https://www.target.com/p/x/-/A-1"
        """,
    )
    config = load_config(config_path, env_path=str(tmp_path / "does-not-exist.env"))
    assert len(config.search_queries) == 1
    assert len(config.products) == 1
