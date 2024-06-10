import pandas
import requests
from sqlalchemy import create_engine


def paged_request_iter(session, url, timeout=1):
    """Generator function for a paged request made with the session.
    Requires session.params["page"] be defined. The page will be incremented
    on the session object. Yields the data for each page and stops when the page
    count exceeds the total number of pages. Raises an HTTPError from
    request.raise_for_status() when the response status is not ok.

    Note that this function is tied to the World Data Bank api format and is not
    generic.

    Params:
      session (requests.Session): Session object for calling the API.
      url (str): The base world data bank api url. Queary params will be set on
        on the session.
      timeout (int): Seconds to wait for a succesfull API connection.

    Example:

    data = []
    for page_data in paged_request_iter(session, url):
        data.extend(page_data)
    """
    while True:
        print(f"Read ({session.params['page']}):", url)
        r = session.get(url, timeout=5)

        r.raise_for_status()
        [info, data] = r.json()
        print("Info:", info)
        yield data

        if info["page"] >= info["pages"]:
            break
        else:
            session.params["page"] += 1


class WorldDataBankConnector:
    """Class for an api connector for the World Data Bank API.

    Fields:
      session (requests.Session): A requests session for managing the connection
        to the API.
      series (str): A series indicator id for the series to queary.
        E.g. "SP.POP.TOTL" is the indicator id for Yearly Population Total.
      start_date (int): Start date for collecting records from the series. If
        end_date is not defined then records for only this date will be collected.
      end_date (int): End date for collecting records from the range in a series.
        Defaults to None for collecting a single date.
      country (str): Countries to collect data for. Defaults to "all" to collect
        data for all available countries. Accepts iso2 country codes separated
        by a ; if there are more than one. E.g. "ca" or "ca;us;mx".
    """

    # Initialize the request session and API call info
    def __init__(
        self, session, series, start_date, end_date=None, country="all"
    ):
        self.session = session
        self.session.params = {
            "format": "json",
            "date": self._make_date_param(start_date, end_date),
            "page": 1,
        }
        self.url = self._make_url(series, country)

    def _refresh(self):
        """Sets the queary params page back to 1. This can allow the same
        connector to be used to queary paged results more than once, otherwise
        a new connector would be needed with a new request session.
        """
        self.session.params["page"] = 1

    def _make_date_param(self, start, end=None):
        """Create a date queary param from the start and end date.

        If there is only a start date then just that date is submitted. If there
        is a start and end date then they are joined into a range as specified by
        the world data bank api as 'start:end'

        Dates must be those that are valid forms for the series being queried.
        """
        return ":".join([str(start), str(end)]) if end else str(start)

    def _make_url(self, series, country="all"):
        """Create the api base url with the series and country."""
        return f"https://api.worldbank.org/v2/country/{country}/indicator/{series}"

    def queary_json(self):
        """Make a queary and return the results as a list of json objects.

        Will raise an HTTPError if there is a problem with the status on the request.

        Does not validate the response if a valid response is returned, but there
        was a problem with the request. E.g. if the series was not found. For the
        purposes of this test this is good enough, but in production code all possible
        responses would need to be handled along with bad http status codes.
        """
        self._refresh()
        data = []
        for page in paged_request_iter(self.session, self.url):
            data.extend(page)
        return data

    def queary_to_sql(self, db_conn, table_name):
        """Make a queary and load the results into the db table.

        If the table exists this will append new results. If there is a primary
        key it should error if trying to insert duplicate records, however, if
        there is not a primary key then it is possible to add duplicates. This is
        the case with the script currently as I am using the pandas df.to_sql
        to create the db if it does not exist and without a schema it does not
        add an appropriate primary key. In production this would not be acceptable.
        """
        data = self.queary_json()
        print(f"Load {len(data)} rows into dataframe...")
        df = pandas.json_normalize(data, sep="_")
        df = df.rename({x: x.upper() for x in df.columns}, axis=1)
        return df.to_sql(table_name, db_conn, if_exists="append", index=False)


def queary(db_name, table_name, series, start, end, country):
    """Quearies the world data bank API and stores the results in the given
    database and table. The database must be an sqlite3 database file.

    Params:
      session (requests.Session): A requests session for managing the connection
        to the API.
      series (str): A series indicator id for the series to queary.
        E.g. "SP.POP.TOTL" is the indicator id for Yearly Population Total.
      start_date (int): Start date for collecting records from the series. If
        end_date is not defined then records for only this date will be collected.
      end_date (int): End date for collecting records from the range in a series.
        Defaults to None for collecting a single date.
      country (str): Countries to collect data for. Defaults to "all" to collect
        data for all available countries. Accepts iso2 country codes separated
        by a ; if there are more than one. E.g. "ca" or "ca;us;mx".
    """
    # Setup the connector
    session = requests.Session()
    conn = WorldDataBankConnector(session, series, start, end, country)

    # Open the db
    engine = create_engine(f"sqlite:///{db_name}")
    with engine.connect() as db:
        conn.queary_to_sql(db, table_name)


if __name__ == "__main__":
    # Common Values
    DB_FILE = "world_data_bank.sqlite3"
    TABLE = "world_data_bank"
    START = 2000
    END = 2023
    COUNTRIES = "ca;us;mx;br;ar;cl;gb;fr;es;de;nl;it;cn;id;in;pk;jp;kp"

    # Build database with Total Population, Birth Rate, and Death Rate series
    queary(DB_FILE, TABLE, "SP.POP.TOTL", START, END, COUNTRIES)
    queary(DB_FILE, TABLE, "SP.DYN.CBRT.IN", START, END, COUNTRIES)
    queary(DB_FILE, TABLE, "SP.DYN.CDRT.IN", START, END, COUNTRIES)
