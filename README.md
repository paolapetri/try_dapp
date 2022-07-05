#  Instructions

1. read <https://medium.com/coinmonks/coding-a-smart-world-series-330fe8b27db9>
2. ``` virtualenv venv ```
3. ``` source venv/bin/activate ```
4. ``` npm install truffle -g ```
5. ``` cd nft_lottery ```
6. ``` sudo truffle compile ```
7. ``` ganache ```
8. copy one of the private key into <b>nft_contract.py</b> ```local_acct = w3.eth.account.from_key("0x4f65b0950f0cbb95585c211733c418479e3ab15d57d9844a46d8c6c138875d08")```
9. run ``` python3 app.py ```


celery -A background worker -l debug
celery -A background beat -l debug

celery -A background worker -l debug -B