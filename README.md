# api-connector-test

Scripts for the ALDC developer test.

`connector.py` contains a class for connecting to the World Data Bank API and a script that will create a sqlite database with series data for total population, birth rate, and death rate.

`visualization.py` contains a script that will construct 3 static visualizations using the database constructed by `connector,py` and one interactive visualization.

`test_connector.py` contains a few simple unit tests to test the components of `connector.py` without calling the API directly or modifying a proper database. Tests can be run by executing this file.

Note: I used the black python code formatter to keep my code formating consistent. Some choices it makes can feel a bit akward, but it is nice not to have to worry about formatting. I am happy to adapt to other styles as required/desired.

## Usage

To generate the database run `$ python3 connector.py`. This will construct a sqlite3 database `world_data_bank.sqlite3` in the folder containing the script.

To generate the visualizations run `$ python3 visualizations.py`. This should open 3 browser windows showing the first 3 plots. The script will then start a server for the 4th interactive visualization which may open in the browser automatically, however, you may have to copy the link displayed in the terminal to navigate to the visualization.

In case there are any issues I have put a copy of the database and some images for the visualizations in releases for download.

## Dependencies

The following python packages are required for the scripts to run. All should be installable with pip.
* requests
* pandas
* sqlalchemy
* plotly
* dash
* packaging (I had to add this for plotly to work on my machine)
* unittest (if you want to run the test file)

## Thoughts

I have compiled a few thoughts on my solutions below. Some of the information below is also included in code doc comments where applicable.

### Paged Data

I handled paged data with a generator function. This allows the request to collect each page of data in a simple for loop for processing. In the code I simply aggregated that data into a single list of JSON objects and passed them to a data frame to be placed in a database. However, were one dealing with large collections of paged data it would likely be more efficient to process each page individually. This could be done by passing each page of data to a data frame and dumping it to the database or by writing some custom code to process the page and properly insert records into the database that way. What would be best depends on context.

### Script Robustness

A primary concern with the code provided for connecting to the API is that it is not very robust. For the scope of this test and the time frame I think this is reasonable, but I would like to note that I am aware of the flaw. The context of how the code is called would determine how request and database errors are handled. Currently, bad http statuses on a response with raise an error and any invalid request that returns a valid response will cause an error when the code trys to process the response as if it contains valid series data.

In addition, the current code builds the database from the series data directly when dumping JSON into a pandas data frame and then to a sqlite3 database. In production the database would have a predetermined schema with proper primary keys. If the connector tried to add duplicate data an error would occur and could be handled, or code could be setup to ignore or update duplicate records.

### Testing

I have added some simple unit tests to avoid calling the API and interacting with a proper database. The connector accepts a requests session object to make this possible by mocking it out and returning test JSON data. The tests that need a database construct a simple one in memory with sqlalchemy and discard it when the test is finished. I could provide more robust tests, but what I have was sufficient to ensure that I was calling the API properly and processing the data as expected without needlessly calling the API for every change or creating and deleting a database for each test run.

### SQL Query

My SQL is a bit rusty, but I tried to provide some reasonable queries that did all the data processing before being used for visualizations. In a small test like this it would be possible to just load the database into a data frame and manipulate it from there. However, I am sure in production it is necessary when working with large data and complex queries to use SQL for as much as possible to keep things efficient.

I was not entirely clear if the test wanted all series to be stored in the same table. This seemed like what was desired with the generic series database table style. I put three different series into the same table and accessed them together where needed. I used temporary tables using a `WITH` statement and then joined them where necessary to combine data from each series. I am not sure if this is the best way to accomplish this, but it worked well enough for the test. There may be more elegant ways to store and combine the data.
Other than joining different series data I used the `LAG()` function to create population growth data for a year. This allowed using the previous year's population data to determine the population change year to year. I think it might have been more appropriate to use `LEAD()`, but it depends on when the population totals are measured in a year. So, when viewing the data it is possible that the growth shown for a year should be shown for the previos year. E.g. some countries population growth was dramatically smaller in 2021 during the pandemic, but it may be that those smaller growth years should have been 2020 which is the first year of the pandemic when restrictions were highest, though I think death rates were much higher in subsequent years. However, this is a data analysis problem and does not affect the technical aspect of the SQL query itself.

### Visualizations

I created three simple static visualizations and one interactive visualization with plotly. The visualizations are not very complex, or beautiful, but should be sufficient to show that I can create them. I am also not sure that the analysis they present is terribly interesting, but since this is a test I think it is sufficient.

The first visualization is a grouped bar chart showing population growth per 1000 people for Canada, The United States, and Mexico. This visualization required using some slightly more involved plot code, but allowed for a nice comparison of the data foe each country over the years shown.

The second visualization is a scatter plot of birth and death rates for countries in The Americas, Europe, and Asia. I think that this plot is a bit cluttered, but it shows some interesting relationships between births and deaths for different countries. It is a bit misleading because the dots for countries are not necessarily in a nice linear order, but can appear to be moving in a particular direction when the years might not line up as expected. I added the year to the hover text so that it is possible to tell when each instance was recorded. It is also possible to click on the legend to hide a set of dots which can make it easier to see a specific set of countries. Probably if this data was desirable some interaction that would narrow the scope or present a selection of countries at one time would make it easier to see trends. Even so, it is possible to see that several European countries have much higher death rates than birth rates, which is something that is generally discussed in the news now and then.

The third visualization is a bar chat with total deaths for each country stacked for each year. This shows the combined deaths for each country in each bar and colors sections of the bar with the deaths for each country. Again, this plot is a bit cluttered, but can make it possible to see which countries make up the majority of deaths each year, generally those with highest population. There might be better ways to present this analysis, but I wanted to give some varied visualizations to show I can. With more time and specific analysis goals I could produce more useful visualizations.

Finally, the fourth visualization is interactive. It aggregates the country data by region and presents line plots of three different population measures. Your can select the six countries from The Americas, Europe, or Asia separately, this helps avoid the cluttering problem on a few of the previous plots. It is also possible to select the total population, raw population growth, and population growth per 1000 people. There are some mildly interesting insights to be gained from this set of visualizations. Specifically, the growth per 1000 people shows that some smaller countries are growing at a much higher rate than larger countries. This is also where one can see the effects of the pandemic on recent years' growth, though as noted above the changes may lag behind by a year.

### Final Thoughts

I think that this test show what I am capable of to a degree. Given the time frame and the open-ended nature of the test there are things that I would be able to do better in production. Also, some of the tasks are things that I have not done for a little while and required/will require a little time to refresh my knowledge and continue to learn best practices and techniques. I am up for this challenge and have enjoyed the test. I think it shows that I can write relatively clean code and consider the issues that are important to the domain.
