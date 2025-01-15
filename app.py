# 14JAN2025 - https://github.com/aztronome/cryptorder.git
# This code mostly works and does what I want including persistance of the values
# A consistent average price regardless of investment amount or number
# of orders - I am making this save before adding the coin symbol to the submit
# function which will display the selected coin sybmol throughout the output

from flask import Flask, render_template, request, jsonify
import ccxt

app = Flask(__name__)
exchange = ccxt.coinbase()  # Use Coinbase exchange

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_price/<coin>', methods=['GET'])
def get_price(coin):
    try:
        if coin == 'BTC':
            ticker = exchange.fetch_ticker('BTC/USD')
        elif coin == 'ETH':
            ticker = exchange.fetch_ticker('ETH/USD')
        elif coin == 'SOL':
            ticker = exchange.fetch_ticker('SOL/USD')
        elif coin == 'SUI':
            ticker = exchange.fetch_ticker('SUI/USD')
        else:
            return jsonify({"error": "Unknown coin"}), 400

        price = ticker['last']  # Get the last price
        return jsonify({"price": price})
    
    except Exception as e:
        print(f"Error fetching price for {coin}: {e}")  # Log the error
        return jsonify({"error": str(e)}), 500

@app.route('/submit', methods=['POST'])
def submit():
    try:
        # Retrieve input values from the form
        current_price = float(request.form['price'])
        investment = float(request.form['investment'])
        percent = float(request.form['percent'])
        bottom_price = float(request.form['bottom_price'])
        scaling_factor = float(request.form['scaling_factor'])
        num_orders = int(request.form['num_orders'])

        # Calculate the first order price, price range, and order width
        first_order_price = current_price * (1 - (percent / 100))
        price_range = first_order_price - bottom_price
        order_width = price_range / (num_orders - 1)

        # Create a normalized weight distribution based on the scaling factor
        weights = []
        for i in range(num_orders):
            weight = (1 + scaling_factor * (num_orders - i - 1) / ((num_orders - 1) * 3.5))
            weights.append(weight)
        
        # Normalize weights to ensure they sum to 1
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        # Calculate orders
        orders = []
        total_investment = 0
        total_quantity = 0

        for i in range(num_orders):
            order_price = round((bottom_price + (i * order_width)), 2)
            order_amount = round(normalized_weights[i] * investment, 2)  # Proportional to the weight
            order_quantity = round(order_amount / order_price, 8)

            total_investment += order_amount
            total_quantity += order_quantity

            orders.append({
                'price': order_price,
                'amount_usd': order_amount,
                'amount_btc': order_quantity
            })

        # Calculate the average cost
        avg_cost = total_investment / total_quantity if total_quantity else 0

        return render_template(
            'index.html',
            orders=orders,
            avg_cost=round(avg_cost, 2),
            total_investment=round(total_investment, 2),
            total_btc=round(total_quantity, 8)
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)