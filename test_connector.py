import unittest
import connector
from sqlalchemy import text, create_engine

# Some simple tests to ensure that the fundamental parts of my code are working
# without quearying the API a million times or requiring a database file.
#
# If this were production code the connector code and the tests would need to
# be more robust for handling api request issues and possible errors. However,
# for the test I don't really have the time to cover every possible issue.
# To keep things simple I did not use a mocking library, but I do mock out the
# requests session object manually so that testing the functionality does not
# queary the API. I have added a couple simple json responses as test data from
# actual API calls.


# Test Data ###################################################################
page1 = [
    {
        "page": 1,
        "pages": 2,
        "per_page": 1,
        "total": 1,
        "sourceid": "2",
        "lastupdated": "2024-05-30",
    },
    [
        {
            "indicator": {
                "id": "SP.POP.TOTL",
                "value": "Population, total",
            },
            "country": {"id": "CA", "value": "Canada"},
            "countryiso3code": "CAN",
            "date": "2000",
            "value": 30685730,
            "unit": "",
            "obs_status": "",
            "decimal": 0,
        }
    ],
]

page2 = [
    {
        "page": 2,
        "pages": 2,
        "per_page": 1,
        "total": 1,
        "sourceid": "2",
        "lastupdated": "2024-05-30",
    },
    [
        {
            "indicator": {
                "id": "SP.POP.TOTL",
                "value": "Population, total",
            },
            "country": {"id": "US", "value": "United States"},
            "countryiso3code": "USA",
            "date": "2000",
            "value": 282162411,
            "unit": "",
            "obs_status": "",
            "decimal": 0,
        }
    ],
]

db_select_all = [
    (
        "CAN",
        "2000",
        30685730,
        "",
        "",
        0,
        "SP.POP.TOTL",
        "Population, total",
        "CA",
        "Canada",
    ),
    (
        "USA",
        "2000",
        282162411,
        "",
        "",
        0,
        "SP.POP.TOTL",
        "Population, total",
        "US",
        "United States",
    ),
]

db_columns = [
    "COUNTRYISO3CODE",
    "DATE",
    "VALUE",
    "UNIT",
    "OBS_STATUS",
    "DECIMAL",
    "INDICATOR_ID",
    "INDICATOR_VALUE",
    "COUNTRY_ID",
    "COUNTRY_VALUE",
]


# Simple Mock response
class MockResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


# Simple Mock Session for testing, so I don't call the API a million times ####
class MockSession:
    def __init__(self, params={}):
        self.params = params
        self.urls = []

    # Returns some test data, with 2 pages and 1 item per page
    def get(self, url, timeout=5):
        self.urls.append(url)
        pages = [
            page1,
            page2,
        ]

        # Check if the request is within the page count and respond accordingly
        page = int(self.params["page"])
        idx = page - 1
        if int(idx > len(pages)):
            # The API returns something like this if the page is out of bounds
            return
            MockResponse(
                [
                    {
                        "page": page,
                        "pages": 2,
                        "per_page": 1,
                        "total": 1,
                        "sourceid": "2",
                        "lastupdated": "2024-05-30",
                    },
                    [],
                ]
            )
        else:
            return MockResponse(pages[idx])


# Testing paged request #######################################################
class TestPagedRequestIterator(unittest.TestCase):
    def test_it_gets_all_pages(self):
        response_data = []
        for data in connector.paged_request_iter(
            MockSession({"page": 1}), "test/url"
        ):
            response_data.append(data)

        self.assertEqual(len(response_data), 2)
        self.assertEqual(response_data[0], page1[1])
        self.assertEqual(response_data[1], page2[1])


# Testing for the connector ###################################################
class TestWorldDataBankConnector(unittest.TestCase):
    def test_init_simple(self):
        session = MockSession()
        date = 2000
        series = "SP.POP.TOTL"
        country = "all"
        url = f"https://api.worldbank.org/v2/country/{country}/indicator/{series}"
        conn = connector.WorldDataBankConnector(session, series, date)

        self.assertEqual(conn.session, session)
        self.assertEqual(conn.session.params["format"], "json")
        self.assertEqual(conn.session.params["page"], 1)
        self.assertEqual(conn.session.params["date"], str(2000))
        self.assertEqual(conn.url, url)

    def test_init_date(self):
        session = MockSession()
        start = 2000
        end = 2020
        series = "SP.POP.TOTL"
        conn = connector.WorldDataBankConnector(session, series, start, end)

        self.assertEqual(conn.session.params["date"], "2000:2020")

    def test_init_country(self):
        session = MockSession()
        date = 2000
        series = "SP.POP.TOTL"
        country = "can"
        url = f"https://api.worldbank.org/v2/country/{country}/indicator/{series}"
        conn = connector.WorldDataBankConnector(
            session, series, date, country=country
        )

        self.assertEqual(conn.url, url)

    def test_query_and_return_json_data(self):
        conn = connector.WorldDataBankConnector(
            MockSession(), "SP.POP.TOTL", 1990, 2000, "all"
        )
        expect = [*page1[1], *page2[1]]
        data = conn.queary_json()

        self.assertEqual(data, expect)

    def test_queary_to_sql(self):
        conn = connector.WorldDataBankConnector(
            MockSession(), "SP.POP.TOTL", 2000, "all"
        )
        engine = create_engine("sqlite://")
        with engine.connect() as db:
            conn.queary_to_sql(db, "world_data_bank")
            entries = db.execute(text("SELECT * FROM world_data_bank"))
            self.assertEqual(entries.keys(), db_columns)
            self.assertEqual(entries.all(), db_select_all)


if __name__ == "__main__":
    try:
        unittest.main()
    except SystemExit:
        pass
