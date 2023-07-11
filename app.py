import streamlit as st
from ebaysdk.finding import Connection as Finding
from ebaysdk.exception import ConnectionError
from datetime import datetime, timedelta

YOUR_APP_ID = "KyleMiri-Reseller-PRD-0182648e2-20610f48"  # replace with your own eBay API key

if YOUR_APP_ID is None:
    raise ValueError("EBAY_APP_ID environment variable not set")

CONDITIONS = {
    'None': (None, None),
    'New': ('New', '1000'),
    'Used': ('Used', '3000'),
    'For parts': ('For parts', '7000')
}

SORT_ORDERS = {
    'Best Match': 'BestMatch',
    'Price + Shipping Lowest': 'PricePlusShippingLowest',
    'Price + Shipping Highest': 'PricePlusShippingHighest',
    'Newly Listed': 'StartTimeNewest',
    'Ending Soonest': 'EndTimeSoonest'
}

api_call_counter = 0

def get_active_listings(pages, item_name, condition_name, sort_order_name):
    global api_call_counter
    if api_call_counter >= 5:
        st.write("Maximum API call limit reached. Please try again later.")
        return

    condition_id = CONDITIONS[condition_name][1]
    condition_text = CONDITIONS[condition_name][0]
    sort_order = SORT_ORDERS[sort_order_name]

    api = Finding(appid=YOUR_APP_ID, config_file=None, siteid="EBAY-US", domain="svcs.ebay.com")

    try:
        prices = []
        items = []
        for page in range(1, pages + 1):
            request = {
                'keywords': item_name,
                'paginationInput': {
                    'entriesPerPage': 100,
                    'pageNumber': page
                },
                'sortOrder': sort_order
            }
            if condition_id is not None:
                request['itemFilter'] = [{'name': 'Condition', 'value': condition_id}]

            response = api.execute('findItemsByKeywords', request)
            api_call_counter += 1

            if response.reply.ack == 'Success':
                searchResult = response.dict()['searchResult']
                if 'item' in searchResult:
                    items += searchResult['item']
                    prices += [(float(item['sellingStatus']['currentPrice']['value']), item['viewItemURL']) for item in searchResult['item']]

        return items, prices

    except ConnectionError as e:
        st.error('Failed to connect to eBay API: {}'.format(e))
    except KeyError as e:
        st.error('KeyError: {}'.format(e))

def get_average_sold_price(pages, item_name, condition_name):
    global api_call_counter
    if api_call_counter >= 5:
        st.write("Maximum API call limit reached. Please try again later.")
        return

    condition_id = CONDITIONS[condition_name][1]
    condition_text = CONDITIONS[condition_name][0]

    api = Finding(appid=YOUR_APP_ID, config_file=None, siteid="EBAY-US", domain="svcs.ebay.com")

    try:
        prices = []
        items = []
        for page in range(1, pages + 1):
            # Get the current time and one year ago
            now = datetime.now()
            one_year_ago = now - timedelta(days=365)

            # Convert to the format expected by the eBay API
            now_str = now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            one_year_ago_str = one_year_ago.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

            # Make the API request
            request = {
                'keywords': item_name,
                'paginationInput': {
                    'entriesPerPage': '100',
                    'pageNumber': str(page)
                },
                'sortOrder': 'EndTimeSoonest',
                'itemFilter': [
                    {'name': 'SoldItemsOnly', 'value': 'true'},
                    {'name': 'EndTimeFrom', 'value': one_year_ago_str},
                    {'name': 'EndTimeTo', 'value': now_str}
                ]
            }
            if condition_id is not None:
                request['itemFilter'].append({'name': 'Condition', 'value': condition_id})

            response = api.execute('findCompletedItems', request)
            api_call_counter += 1

            # Check if the call was successful
            if response.reply.ack == 'Success':
                searchResult = response.dict()['searchResult']
                if 'item' in searchResult:
                    items += searchResult['item']
                    prices += [(float(item['sellingStatus']['currentPrice']['value']), item['viewItemURL']) for item in searchResult['item']]

        return items, prices

    except ConnectionError as e:
        st.error('Failed to connect to eBay API: {}'.format(e))
    except KeyError as e:
        st.error('KeyError: {}'.format(e))

def main():
    global api_call_counter
    api_call_counter = 0

    st.title('Ebay Listings Analyzer')
    pages = st.number_input("How many pages would you like to retrieve?", min_value=1, max_value=100, value=1)
    item_name = st.text_input("What item would you like to analyze?")
    condition_name = st.selectbox("What condition should the item be in?", list(CONDITIONS.keys()))
    sort_order_name = st.selectbox("How would you like to sort the results?", list(SORT_ORDERS.keys()))
    listings_type = st.selectbox("Which type of listings would you like to analyze?", ["Active", "Completed", "Both"])

    if st.button('Analyze'):
        if listings_type in ["Active", "Both"]:
            items, prices = get_active_listings(pages, item_name, condition_name, sort_order_name)
            # Calculate the average, low, and high prices
            average_price = sum(price for price, _ in prices) / len(prices) if prices else 0
            low_price, low_price_link = min(prices, default=(0, None))
            high_price, high_price_link = max(prices, default=(0, None))
            # Get the most recent listing
            most_recent_listing = max(items, key=lambda item: item['listingInfo']['startTime'])
            most_recent_listing_link = most_recent_listing['viewItemURL']
            most_recent_listing_price = float(most_recent_listing['sellingStatus']['currentPrice']['value'])
            st.markdown(f'Found **{len(items)}** active listings for <span style="color:orange;">{item_name}</span> in <span style="color:orange;">{condition_name}</span> condition:', unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: left; color: green;'>Average price:</h2>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: left; color: white;'>${average_price:.2f}</h3>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: left; color: yellow;'>Low price:</h2>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: left; color: white;'><a href='{low_price_link}' target='_blank'>${low_price:.2f}</a></h3>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: left; color: blue;'>High price:</h2>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: left; color: white;'><a href='{high_price_link}' target='_blank'>${high_price:.2f}</a></h3>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: left; color: magenta;'>Most recent listing price:</h2>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: left; color: white;'><a href='{most_recent_listing_link}' target='_blank'>${most_recent_listing_price:.2f}</a></h3>", unsafe_allow_html=True)

        if listings_type in ["Completed", "Both"]:
            items, prices = get_average_sold_price(pages, item_name, condition_name)
            # Calculate the average, low, and high prices
            average_price = sum(price for price, _ in prices) / len(prices) if prices else 0
            low_price, low_price_link = min(prices, default=(0, None))
            high_price, high_price_link = max(prices, default=(0, None))
            # Get the most recent listing
            most_recent_listing = max(items, key=lambda item: item['listingInfo']['endTime'])
            most_recent_listing_link = most_recent_listing['viewItemURL']
            most_recent_listing_price = float(most_recent_listing['sellingStatus']['currentPrice']['value'])
            st.markdown(f'Found **{len(items)}** completed listings for <span style="color:orange;">{item_name}</span> in <span style="color:orange;">{condition_name}</span> condition:', unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: left; color: green;'>Average sold price:</h2>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: left; color: white;'>${average_price:.2f}</h3>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: left; color: yellow;'>Lowest price sold:</h2>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: left; color: white;'><a href='{low_price_link}' target='_blank'>${low_price:.2f}</a></h3>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: left; color: blue;'>Highest price sold:</h2>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: left; color: white;'><a href='{high_price_link}' target='_blank'>${high_price:.2f}</a></h3>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: left; color: magenta;'>Most recent sold price:</h2>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: left; color: white;'><a href='{most_recent_listing_link}' target='_blank'>${most_recent_listing_price:.2f}</a></h3>", unsafe_allow_html=True)

        st.markdown("<h2 style='text-align: left; color: white;'><a href='https://www.ebay.com' target='_blank'>View the eBay listing for yourself here!</a></h2>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
