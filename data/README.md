# Source workbook

Chen, D. (2015). Online Retail [Dataset].
UCI Machine Learning Repository.
https://doi.org/10.24432/C5BW33

Dataset page: https://archive.ics.uci.edu/dataset/352/online+retail
License: Creative Commons Attribution 4.0 (CC BY 4.0).

Download the dataset and extract the workbook if supplied in an archive.
Place a copy at data/Online Retail.xlsx. Preserve the original workbook.
Alternatively, pass another quoted workbook path using --input.

The first worksheet must contain:
InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice,
CustomerID, Country.

Prices are recorded in GBP. Missing values observed in the workbook take
precedence over conflicting source metadata.

The verified workbook has 541,909 rows. Its SHA-256 is:
43465a06f2ccf7c8b5bd2892bc7defb52f97487934fe93b16ae4c3936424676d

The application calculates the hash and raw profile on every run.
Different workbook bytes can produce a different hash.

Raw workbooks are excluded from Git and Docker. Container runs obtain the
workbook through a read-only bind mount.

The December 2011 partial-month rule is specific to this source and must
be reviewed before using another dataset.