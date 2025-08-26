# Intelligent Web Scraper Dashboard

A comprehensive Streamlit-based dashboard for monitoring and managing web scraping operations with real-time updates, interactive visualizations, and AI-powered content analysis.

## Features

### 🚀 Job Management
- **Create Jobs**: Interactive form with advanced configuration options
- **Monitor Progress**: Real-time job status tracking with progress bars
- **Bulk Operations**: Start, stop, or cancel multiple jobs at once
- **Job Templates**: Save and reuse common scraping configurations
- **Priority Management**: Set job priorities for queue optimization

### 🔍 Data Explorer
- **Interactive Filtering**: Filter by confidence score, quality, date range
- **Content Preview**: View extracted content with syntax highlighting
- **Search Functionality**: Full-text search across scraped content
- **Export Options**: Download data in CSV, JSON, or Excel formats
- **Quality Metrics**: View data quality scores and validation errors

### 📊 Analytics & Visualization
- **Performance Charts**: Real-time scraping rate and response time trends
- **Quality Distribution**: Visualize data quality across all records
- **Domain Analysis**: See which domains are being scraped most
- **Error Analysis**: Track and categorize scraping errors
- **Content Type Breakdown**: Analyze different types of scraped content

### 🖥️ System Monitoring
- **Resource Usage**: Monitor CPU, memory, and disk utilization
- **Service Health**: Check status of API, database, Redis, and workers
- **Performance Metrics**: Track scraping rates and system throughput
- **Historical Data**: View trends over time with customizable time ranges
- **Alerts**: Get notified of system issues and performance problems

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Dashboard

```bash
# Simple start
python run_dashboard.py

# Custom configuration
python run_dashboard.py --host localhost --port 8502 --debug
```

### 3. Access the Dashboard

Open your browser and navigate to:
- Default: http://localhost:8501
- Custom: http://localhost:[your-port]

## Dashboard Structure

```
src/dashboard/
├── main.py                     # Main dashboard application
├── components/                 # Reusable dashboard components
│   ├── job_management.py      # Job creation and monitoring
│   ├── data_visualization.py  # Data exploration and charts
│   └── system_metrics.py      # System health monitoring
├── utils/                     # Utility modules
│   ├── data_loader.py        # Data loading and caching
│   └── session_manager.py    # Session state management
└── README.md                  # This file
```

## Usage Guide

### Navigation

The dashboard uses a sidebar navigation with the following pages:

1. **Overview**: High-level metrics and recent activity
2. **Job Management**: Create, monitor, and manage scraping jobs
3. **Data Explorer**: Browse and analyze scraped data
4. **System Metrics**: Monitor system health and performance
5. **Settings**: Configure dashboard preferences

### Creating a Scraping Job

1. Navigate to **Job Management** → **Create Job** tab
2. Enter the target URL
3. Configure scraping options:
   - **Basic**: Wait time, retries, priority
   - **Advanced**: Browser settings, extraction options
   - **Selectors**: Custom CSS selectors for specific data
4. Click **Create Job** to submit

### Monitoring Jobs

1. Go to **Job Management** → **Active Jobs** tab
2. Use filters to find specific jobs
3. View real-time progress and status
4. Use bulk actions for multiple jobs
5. Click job details for logs and metrics

### Exploring Data

1. Navigate to **Data Explorer** → **Data Explorer** tab
2. Apply filters:
   - Job ID, confidence score, quality score
   - Date range, AI processing status
3. Search content using the search box
4. Select records to view detailed content
5. Export filtered data in your preferred format

### System Monitoring

1. Go to **System Metrics** for real-time monitoring
2. Check **System Health** for current status
3. View **Performance** metrics and trends
4. Monitor **Services** status and health
5. Analyze **Historical** data for trends

## Configuration

### Auto-Refresh Settings

- **Enable/Disable**: Toggle automatic data refresh
- **Interval**: Set refresh frequency (1-60 seconds)
- **Manual Refresh**: Force immediate data update

### Display Options

- **Theme**: Light/Dark mode (future feature)
- **Page Size**: Number of records per page
- **Chart Height**: Customize visualization height
- **Sidebar**: Show/hide metrics sidebar

### Export Settings

- **Format**: Default export format (CSV, JSON, Excel)
- **Include Metadata**: Add extraction metadata to exports
- **Max Records**: Limit for large exports
- **Compression**: Enable file compression

## Advanced Features

### Real-Time Updates

The dashboard automatically refreshes data based on your settings:
- Job status updates every 5 seconds (default)
- System metrics update every 15 seconds
- Charts and visualizations update with new data

### Caching

Data is cached to improve performance:
- Job statistics: 30 seconds
- System health: 15 seconds
- Analytics data: 5 minutes
- Manual cache clearing available

### Session Management

Your preferences are automatically saved:
- Filter settings persist across sessions
- Navigation history is maintained
- Notification preferences are remembered
- Dashboard layout preferences are saved

### Error Handling

The dashboard gracefully handles errors:
- Network connectivity issues
- Database connection problems
- Invalid data or configuration
- Service unavailability

## Troubleshooting

### Common Issues

**Dashboard won't start:**
```bash
# Check dependencies
python run_dashboard.py --no-check

# Try different port
python run_dashboard.py --port 8502
```

**Data not loading:**
- Check database connection
- Verify API service is running
- Clear cache in Settings
- Check browser console for errors

**Performance issues:**
- Enable performance mode in Settings
- Reduce refresh frequency
- Limit data display (smaller page sizes)
- Clear browser cache

**Charts not displaying:**
- Ensure Plotly is installed
- Check browser JavaScript is enabled
- Try refreshing the page
- Clear Streamlit cache

### Debug Mode

Enable debug mode for detailed logging:
```bash
python run_dashboard.py --debug
```

This will show:
- Detailed error messages
- Data loading times
- Component rendering information
- Network request details

### Log Files

Dashboard logs are available in:
- Console output (when running)
- Application logs (if configured)
- Browser developer tools (client-side errors)

## API Integration

The dashboard integrates with the scraping system APIs:

- **Job API**: Create, monitor, and control jobs
- **Data API**: Retrieve and filter scraped data
- **Metrics API**: Get system performance data
- **Health API**: Check service status

## Security

The dashboard includes security features:
- Input validation and sanitization
- CSRF protection (when enabled)
- Rate limiting for API calls
- Secure session management

## Performance Optimization

For better performance:
- Use caching effectively
- Limit data display ranges
- Enable performance mode
- Use appropriate refresh intervals
- Monitor system resources

## Contributing

To contribute to the dashboard:

1. Follow the existing code structure
2. Add tests for new components
3. Update documentation
4. Follow Python coding standards
5. Test with different data scenarios

## Support

For issues or questions:
- Check the troubleshooting section
- Review application logs
- Test with minimal configuration
- Report bugs with detailed information