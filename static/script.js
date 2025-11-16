// Allow Enter key to trigger search
document.getElementById('tickerInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        searchRatings();
    }
});

function searchRatings() {
    const ticker = document.getElementById('tickerInput').value.trim().toUpperCase();
    
    if (!ticker) {
        showError('Please enter a ticker symbol');
        return;
    }

    // Show loading state
    document.getElementById('loading').style.display = 'block';
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('errorMessage').style.display = 'none';
    document.getElementById('searchBtn').disabled = true;
    document.getElementById('searchBtn').textContent = 'Fetching...';

    // Initialize results display immediately
    initializeResultsDisplay(ticker);

    // Use single parallel request (fastest approach)
    fetch('/get_ratings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ticker: ticker })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showError(data.error);
        } else {
            // Simulate progressive loading for better UX
            displayResultsProgressively(data);
        }
    })
    .catch(error => {
        showError('Network error: ' + error.message);
    })
    .finally(() => {
        document.getElementById('searchBtn').disabled = false;
        document.getElementById('searchBtn').textContent = 'Get Ratings';
    });
}

function displayResultsProgressively(data) {
    // Update ticker with stock name and ticker symbol
    updateTickerDisplay(data.ticker, data.price ? data.price.stock_name : null);
    document.getElementById('timestamp').textContent = 'Updated: ' + data.timestamp;
    
    // Update all platform data immediately (no artificial delays)
    updatePriceDisplay(data.price);
    updatePlatformCard('zacks', data.zacks);
    updatePlatformCard('tipranks', data.tipranks);
    updatePlatformCard('barchart', data.barchart);
    updatePlatformCard('stockopedia', data.stockopedia);
    updatePlatformCard('stockanalysis', data.stockanalysis);
    
    // Update price target display after price is available
    updatePriceTargetDisplay(data.stockanalysis);
    
    // Display consensus immediately
    displayConsensus(data);
    
    // Hide loading indicator
    document.getElementById('loading').style.display = 'none';
}

function updatePlatformCard(platform, data) {
    switch(platform) {
        case 'zacks':
            updateRatingCard('zacks', data, data.rank ? `Rank: ${data.rank}` : '');
            break;
        case 'tipranks':
            updateRatingCard('tipranks', data, data.score ? `Smart Score: ${data.score}/10` : '');
            break;
        case 'barchart':
            updateRatingCard('barchart', data, data.score ? `Score: ${data.score}` : '');
            break;
        case 'stockopedia':
            updateStockopediaCard('stockopedia', data);
            break;
        case 'stockanalysis':
            updateStockAnalysisCard('stockanalysis', data);
            break;
    }
}

function initializeResultsDisplay(ticker) {
    // Show results section early with loading indicators
    document.getElementById('tickerSymbol').textContent = ticker;
    document.getElementById('timestamp').textContent = 'Loading...';
    updatePlatformLinks(ticker);
    
    // Show price loading state (simplified)
    const priceDisplay = document.getElementById('priceDisplay');
    const currentPrice = document.getElementById('currentPrice');
    const priceChange = document.getElementById('priceChange');
    currentPrice.textContent = '⏳';
    priceChange.textContent = '';
    priceChange.className = 'price-change';
    priceDisplay.style.display = 'inline-block';
    
    // Show price target loading state
    const priceTargetDisplay = document.getElementById('priceTargetDisplay');
    const targetPrice = document.getElementById('targetPrice');
    const priceDifference = document.getElementById('priceDifference');
    targetPrice.textContent = '⏳';
    priceDifference.style.display = 'none'; // Hide until data is ready
    priceTargetDisplay.style.display = 'inline-block';
    
    // Show all cards with loading state
    const platforms = ['zacks', 'tipranks', 'barchart', 'stockopedia', 'stockanalysis'];
    platforms.forEach(platform => {
        const ratingElement = document.getElementById(platform + 'Rating');
        const statusElement = document.getElementById(platform + 'Status');
        const scoreElement = document.getElementById(platform + 'Score');
        
        ratingElement.textContent = '⏳';
        ratingElement.className = 'rating-value';
        statusElement.textContent = '...';
        statusElement.className = 'rating-description status-warning';
        
        // Initialize score elements if they exist
        if (scoreElement) {
            scoreElement.textContent = '...';
        }
    });
    
    // Show results section and hide main loading
    document.getElementById('resultsSection').style.display = 'block';
    document.getElementById('loading').style.display = 'none';
}

function displayResults(data) {
    // Update ticker and timestamp
    document.getElementById('tickerSymbol').textContent = data.ticker;
    document.getElementById('timestamp').textContent = 'Updated: ' + data.timestamp;

    // Update platform links
    updatePlatformLinks(data.ticker);

    // Update Zacks
    updateRatingCard('zacks', data.zacks, data.zacks.rank ? `Rank: ${data.zacks.rank}` : '');

    // Update TipRanks
    updateRatingCard('tipranks', data.tipranks, data.tipranks.score ? `Smart Score: ${data.tipranks.score}/10` : '');

    // Update Barchart
    updateRatingCard('barchart', data.barchart, 'Opinion');

    // Update Stockopedia
    updateStockopediaCard('stockopedia', data.stockopedia);

    // Calculate and display consensus
    displayConsensus(data);

    // Show results
    document.getElementById('resultsSection').style.display = 'block';
}

function updatePlatformLinks(ticker) {
    const tickerUpper = ticker.toUpperCase();
    const tickerLower = ticker.toLowerCase();
    
    // Update Zacks links (both card and platform name)
    const zacksUrl = `https://www.zacks.com/stock/quote/${tickerUpper}`;
    document.getElementById('zacksCardLink').href = zacksUrl;
    
    // Update TipRanks links
    const tipranksUrl = `https://www.tipranks.com/stocks/${tickerLower}`;
    document.getElementById('tipranksCardLink').href = tipranksUrl;
    
    // Update Barchart links
    const barchartUrl = `https://www.barchart.com/stocks/quotes/${tickerLower}/overview`;
    document.getElementById('barchartCardLink').href = barchartUrl;
    
    // Update Stockopedia links
    const stockopediaUrl = `https://www.stockopedia.com/share-prices/${tickerLower}-NSQ:${tickerUpper}/`;
    document.getElementById('stockopediaCardLink').href = stockopediaUrl;
    
    // Update Stock Analysis links
    const stockanalysisUrl = `https://stockanalysis.com/stocks/${tickerLower}/forecast/`;
    document.getElementById('stockanalysisCardLink').href = stockanalysisUrl;
}

function updateRatingCard(platform, data, scoreText) {
    const ratingElement = document.getElementById(platform + 'Rating');
    const scoreElement = document.getElementById(platform + 'Score') || document.getElementById(platform + 'Rank');
    const statusElement = document.getElementById(platform + 'Status');

    const rating = data.rating || data.rating || 'N/A';
    
    ratingElement.textContent = rating;
    if (scoreElement) scoreElement.textContent = scoreText;
    
    // Hide status description for these platforms (keep only for stockanalysis)
    statusElement.style.display = 'none';

    // Remove existing rating classes
    ratingElement.className = 'rating-value';
    
    // Add appropriate class based on rating
    const normalizedRating = rating.toLowerCase().replace(/\s+/g, '-');
    ratingElement.classList.add('rating-' + normalizedRating);
}

function updateStockopediaCard(platform, data) {
    const ratingElement = document.getElementById(platform + 'Rating');
    const scoreElement = document.getElementById(platform + 'Score');
    const statusElement = document.getElementById(platform + 'Status');

    const stockrank = data.stockrank || 'N/A';
    const category = data.category || 'Unknown';
    
    ratingElement.textContent = category;
    if (scoreElement) scoreElement.textContent = `StockRank: ${stockrank}/100`;
    
    // Hide status description for Stockopedia
    statusElement.style.display = 'none';

    // Remove existing rating classes
    ratingElement.className = 'rating-value';
    
    // Add appropriate class based on category
    const normalizedCategory = category.toLowerCase().replace(/\s+/g, '-');
    ratingElement.classList.add('rating-' + normalizedCategory);
}

function updateStockAnalysisCard(platform, data) {
    const ratingElement = document.getElementById(platform + 'Rating');
    const analystsElement = document.getElementById(platform + 'Analysts');
    const statusElement = document.getElementById(platform + 'Status');

    const consensus = data.consensus || 'N/A';
    const analysts = data.analyst_count || 'N/A';
    const priceTarget = data.price_target || 'N/A';
    
    ratingElement.textContent = consensus;
    analystsElement.textContent = `Analysts: ${analysts}`;
    statusElement.textContent = priceTarget !== 'N/A' ? `Target: $${priceTarget}` : 'No target';

    // Remove existing rating classes
    ratingElement.className = 'rating-value';
    
    // Add appropriate class based on consensus
    const normalizedConsensus = consensus.toLowerCase().replace(/\s+/g, '-');
    ratingElement.classList.add('rating-' + normalizedConsensus);

    // Set status color
    statusElement.className = 'rating-description';
    if (data.success) {
        statusElement.classList.add('status-success');
    } else {
        statusElement.classList.add('status-error');
    }
}

function updateTickerDisplay(ticker, stockName) {
    const tickerElement = document.getElementById('tickerSymbol');
    
    if (stockName && stockName !== ticker) {
        // Display stock name with ticker in brackets
        tickerElement.textContent = `${stockName} (${ticker})`;
    } else {
        // Fallback to just ticker if no stock name available
        tickerElement.textContent = ticker;
    }
}

function updatePriceDisplay(priceData) {
    const priceDisplay = document.getElementById('priceDisplay');
    const currentPrice = document.getElementById('currentPrice');
    const priceChange = document.getElementById('priceChange');

    if (priceData && priceData.success && priceData.current_price !== 'N/A') {
        const price = priceData.current_price;
        const change = priceData.change;
        const changePercent = priceData.change_percent;

        // Update current price
        currentPrice.textContent = `$${price}`;

        // Update change with appropriate color and sign
        const changeText = `${change >= 0 ? '+' : ''}${change} (${changePercent >= 0 ? '+' : ''}${changePercent}%)`;
        priceChange.textContent = changeText;
        
        // Apply color based on positive/negative
        priceChange.className = 'price-change ' + (change >= 0 ? 'price-positive' : 'price-negative');

        // Show the price display
        priceDisplay.style.display = 'inline-block';
    } else {
        // Hide price display if no data
        priceDisplay.style.display = 'none';
    }
}

function updatePriceTargetDisplay(stockAnalysisData) {
    const priceTargetDisplay = document.getElementById('priceTargetDisplay');
    const targetPrice = document.getElementById('targetPrice');
    const priceDifference = document.getElementById('priceDifference');

    if (stockAnalysisData && stockAnalysisData.success && stockAnalysisData.price_target && stockAnalysisData.price_target !== 'N/A') {
        const target = parseFloat(stockAnalysisData.price_target);
        
        // Update target price
        targetPrice.textContent = `$${target.toFixed(2)}`;

        // Calculate price difference if current price is available
        const currentPriceElement = document.getElementById('currentPrice');
        const currentPriceText = currentPriceElement.textContent;
        
        // Extract current price from text like "$377.04"
        const priceMatch = currentPriceText.match(/\$([0-9,]+\.?[0-9]*)/);
        
        if (priceMatch) {
            const currentPrice = parseFloat(priceMatch[1].replace(/,/g, ''));
            const difference = target - currentPrice;
            const percentDifference = ((difference / currentPrice) * 100);
            
            // Format the difference display
            const sign = difference >= 0 ? '+' : '';
            const diffText = `${sign}${difference.toFixed(2)} (${sign}${percentDifference.toFixed(2)}%)`;
            
            priceDifference.textContent = diffText;
            priceDifference.style.display = 'block';
            
            // Apply color based on positive/negative
            priceDifference.className = 'price-difference ' + (difference >= 0 ? 'positive' : 'negative');
        } else {
            // If current price not available, hide difference completely
            priceDifference.style.display = 'none';
        }

        // Show the price target display
        priceTargetDisplay.style.display = 'inline-block';
    } else {
        // Hide price target display if no data
        priceTargetDisplay.style.display = 'none';
        priceDifference.style.display = 'none';
    }
}

function displayConsensus(data) {
    const consensusElement = document.getElementById('consensusResult');
    const descriptionElement = document.getElementById('consensusDescription');

    // Count positive and negative ratings
    let positive = 0;
    let negative = 0;
    let neutral = 0;
    let total = 0;

    // Analyze Zacks
    if (data.zacks.success) {
        total++;
        const zacksRating = data.zacks.rating.toLowerCase();
        if (zacksRating.includes('strong buy') || zacksRating.includes('buy')) positive++;
        else if (zacksRating.includes('sell')) negative++;
        else neutral++;
    }

    // Analyze TipRanks
    if (data.tipranks.success) {
        total++;
        const tipranksRating = data.tipranks.rating.toLowerCase();
        if (tipranksRating.includes('outperform')) positive++;
        else if (tipranksRating.includes('underperform')) negative++;
        else neutral++;
    }

    // Analyze Barchart
    if (data.barchart.success) {
        total++;
        const barchartRating = data.barchart.rating.toLowerCase();
        if (barchartRating.includes('strong buy') || barchartRating.includes('buy')) positive++;
        else if (barchartRating.includes('sell')) negative++;
        else neutral++;
    }

    // Analyze Stockopedia
    if (data.stockopedia.success) {
        total++;
        const stockopediaCategory = data.stockopedia.category.toLowerCase();
        if (stockopediaCategory.includes('excellent') || stockopediaCategory.includes('good')) positive++;
        else if (stockopediaCategory.includes('poor')) negative++;
        else neutral++;
    }

    // Analyze Stock Analysis
    if (data.stockanalysis.success) {
        total++;
        const stockanalysisConsensus = data.stockanalysis.consensus.toLowerCase();
        if (stockanalysisConsensus.includes('strong buy') || stockanalysisConsensus.includes('buy')) positive++;
        else if (stockanalysisConsensus.includes('sell')) negative++;
        else neutral++;
    }

    // Determine consensus
    let consensus = '';
    let description = '';
    let cssClass = '';

    const majority = Math.ceil(total / 2);

    if (positive >= majority) {
        consensus = '🔥 BUY CONSENSUS';
        description = `${positive} of ${total} platforms recommend buying`;
        cssClass = 'rating-strong-buy';
    } else if (negative >= majority) {
        consensus = '⚠️ SELL CONSENSUS';
        description = `${negative} of ${total} platforms recommend selling`;
        cssClass = 'rating-strong-sell';
    } else if (neutral >= majority) {
        consensus = '📊 HOLD CONSENSUS';
        description = `${neutral} of ${total} platforms recommend holding`;
        cssClass = 'rating-hold';
    } else {
        consensus = '🤔 MIXED SIGNALS';
        description = 'Platforms show conflicting recommendations';
        cssClass = 'rating-neutral';
    }

    consensusElement.textContent = consensus;
    consensusElement.className = 'consensus-result ' + cssClass;
    descriptionElement.textContent = description;
}

function showError(message) {
    const errorElement = document.getElementById('errorMessage');
    errorElement.textContent = message;
    errorElement.style.display = 'block';
    document.getElementById('resultsSection').style.display = 'none';
}