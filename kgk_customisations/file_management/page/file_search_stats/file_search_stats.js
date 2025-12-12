frappe.pages['file-search-stats'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'File Search Statistics',
		single_column: true
	});

	// Add refresh button
	page.set_primary_action(__('Refresh'), function() {
		load_statistics(page);
	}, 'refresh');

	// Load statistics
	load_statistics(page);
};

function load_statistics(page) {
	// Show loading indicator
	page.$body.html(`
		<div class="text-center" style="padding: 50px;">
			<i class="fa fa-spinner fa-spin fa-3x text-muted"></i>
			<p class="mt-3 text-muted">Loading statistics...</p>
		</div>
	`);

	// Fetch statistics
	frappe.call({
		method: 'kgk_customisations.file_management.Utils.indexer.get_file_statistics',
		callback: function(r) {
			if (r.message) {
				render_statistics(page, r.message);
			}
		}
	});
}

function render_statistics(page, stats) {
	const html = `
		<div class="file-stats-container" style="padding: 20px;">
			<!-- Summary Cards -->
			<div class="row mb-4">
				<div class="col-md-3">
					<div class="card text-center" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
						<div class="card-body">
							<i class="fa fa-files-o fa-3x mb-3"></i>
							<h2>${stats.total_files.toLocaleString()}</h2>
							<p class="mb-0">Total Files Indexed</p>
						</div>
					</div>
				</div>
				<div class="col-md-3">
					<div class="card text-center" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white;">
						<div class="card-body">
							<i class="fa fa-database fa-3x mb-3"></i>
							<h2>${stats.total_size_gb.toFixed(2)} GB</h2>
							<p class="mb-0">Total Storage Used</p>
						</div>
					</div>
				</div>
				<div class="col-md-3">
					<div class="card text-center" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white;">
						<div class="card-body">
							<i class="fa fa-search fa-3x mb-3"></i>
							<h2>${stats.total_searches.toLocaleString()}</h2>
							<p class="mb-0">Total Searches</p>
						</div>
					</div>
				</div>
				<div class="col-md-3">
					<div class="card text-center" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); color: white;">
						<div class="card-body">
							<i class="fa fa-cube fa-3x mb-3"></i>
							<h2>${stats.unique_lots.toLocaleString()}</h2>
							<p class="mb-0">Unique Lot Numbers</p>
						</div>
					</div>
				</div>
			</div>

			<!-- File Type Breakdown -->
			<div class="row mb-4">
				<div class="col-md-6">
					<div class="card">
						<div class="card-header">
							<h5 class="mb-0"><i class="fa fa-pie-chart"></i> Files by Type</h5>
						</div>
						<div class="card-body">
							<table class="table table-hover">
								<thead>
									<tr>
										<th>File Type</th>
										<th class="text-right">Count</th>
										<th class="text-right">Storage (GB)</th>
										<th class="text-right">%</th>
									</tr>
								</thead>
								<tbody>
									${renderFileTypeRows(stats.by_type, stats.total_files)}
								</tbody>
							</table>
						</div>
					</div>
				</div>

				<!-- Index Health -->
				<div class="col-md-6">
					<div class="card">
						<div class="card-header">
							<h5 class="mb-0"><i class="fa fa-heartbeat"></i> Index Health</h5>
						</div>
						<div class="card-body">
							<div class="mb-4">
								<div class="d-flex justify-content-between mb-2">
									<span>Last Full Index:</span>
									<strong>${formatDateTime(stats.last_indexed)}</strong>
								</div>
								<div class="d-flex justify-content-between mb-2">
									<span>Index Age:</span>
									<strong>${getTimeAgo(stats.last_indexed)}</strong>
								</div>
								<div class="d-flex justify-content-between mb-2">
									<span>Health Status:</span>
									<span class="badge badge-${getHealthBadge(stats.index_health)}">${stats.index_health}</span>
								</div>
							</div>

							<h6 class="mb-3">Quick Actions</h6>
							<div class="btn-group-vertical w-100">
								<button class="btn btn-primary mb-2" onclick="validateIndex()">
									<i class="fa fa-check-circle"></i> Validate Index
								</button>
								<button class="btn btn-info mb-2" onclick="incrementalIndex()">
									<i class="fa fa-plus-circle"></i> Index New Files
								</button>
								<button class="btn btn-warning" onclick="fullReindex()">
									<i class="fa fa-refresh"></i> Full Reindex
								</button>
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- Recent Searches -->
			<div class="row mb-4">
				<div class="col-md-12">
					<div class="card">
						<div class="card-header">
							<h5 class="mb-0"><i class="fa fa-history"></i> Recent Searches</h5>
						</div>
						<div class="card-body">
							<div id="recent-searches-list">
								${renderRecentSearches(stats.recent_searches)}
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- Storage Trend (Placeholder for future charts) -->
			<div class="row">
				<div class="col-md-12">
					<div class="card">
						<div class="card-header">
							<h5 class="mb-0"><i class="fa fa-line-chart"></i> Storage Distribution</h5>
						</div>
						<div class="card-body">
							<div id="storage-chart" style="height: 300px;">
								${renderStorageChart(stats.by_type)}
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	`;

	page.$body.html(html);
}

function renderFileTypeRows(byType, totalFiles) {
	const typeIcons = {
		'polish_video': 'fa-video-camera text-primary',
		'rough_video': 'fa-film text-info',
		'advisor': 'fa-file-text text-success',
		'scan': 'fa-file-image-o text-warning'
	};

	return byType.map(row => {
		const percentage = ((row.count / totalFiles) * 100).toFixed(1);
		const icon = typeIcons[row.file_type] || 'fa-file';
		return `
			<tr>
				<td><i class="fa ${icon}"></i> ${formatFileType(row.file_type)}</td>
				<td class="text-right">${row.count.toLocaleString()}</td>
				<td class="text-right">${row.size_gb.toFixed(2)}</td>
				<td class="text-right">${percentage}%</td>
			</tr>
		`;
	}).join('');
}

function renderRecentSearches(searches) {
	if (!searches || searches.length === 0) {
		return '<p class="text-muted">No recent searches found.</p>';
	}

	return `
		<table class="table table-sm">
			<thead>
				<tr>
					<th>Lot Number</th>
					<th>Results Found</th>
					<th>Searched At</th>
				</tr>
			</thead>
			<tbody>
				${searches.map(s => `
					<tr>
						<td><a href="/lot-search/${s.lot_number}">${s.lot_number}</a></td>
						<td>${s.results_count} files</td>
						<td>${formatDateTime(s.searched_at)}</td>
					</tr>
				`).join('')}
			</tbody>
		</table>
	`;
}

function renderStorageChart(byType) {
	// Simple ASCII-style bar chart
	const maxSize = Math.max(...byType.map(t => t.size_gb));
	
	return `
		<div style="padding: 20px;">
			${byType.map(type => {
				const width = (type.size_gb / maxSize * 100).toFixed(1);
				const color = {
					'polish_video': '#007bff',
					'rough_video': '#17a2b8',
					'advisor': '#28a745',
					'scan': '#ffc107'
				}[type.file_type] || '#6c757d';
				
				return `
					<div class="mb-3">
						<div class="d-flex justify-content-between mb-1">
							<span>${formatFileType(type.file_type)}</span>
							<span><strong>${type.size_gb.toFixed(2)} GB</strong></span>
						</div>
						<div class="progress" style="height: 30px;">
							<div class="progress-bar" role="progressbar" 
								 style="width: ${width}%; background-color: ${color};"
								 aria-valuenow="${width}" aria-valuemin="0" aria-valuemax="100">
								${type.count.toLocaleString()} files
							</div>
						</div>
					</div>
				`;
			}).join('')}
		</div>
	`;
}

function formatFileType(type) {
	return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function formatDateTime(dt) {
	if (!dt) return 'Never';
	return frappe.datetime.str_to_user(dt);
}

function getTimeAgo(dt) {
	if (!dt) return 'Never indexed';
	return frappe.datetime.comment_when(dt);
}

function getHealthBadge(health) {
	const badges = {
		'Excellent': 'success',
		'Good': 'info',
		'Fair': 'warning',
		'Poor': 'danger'
	};
	return badges[health] || 'secondary';
}

// Global action functions
window.validateIndex = function() {
	frappe.call({
		method: 'kgk_customisations.file_management.Utils.indexer.validate_indexed_files',
		callback: function(r) {
			if (r.message) {
				frappe.show_alert({
					message: r.message.message,
					indicator: r.message.status === 'success' ? 'green' : 'red'
				});
				setTimeout(() => location.reload(), 2000);
			}
		}
	});
};

window.incrementalIndex = function() {
	frappe.call({
		method: 'kgk_customisations.file_management.Utils.indexer.index_new_files_only',
		callback: function(r) {
			if (r.message) {
				frappe.show_alert({
					message: r.message.message,
					indicator: r.message.status === 'success' ? 'green' : 'blue'
				});
				setTimeout(() => location.reload(), 3000);
			}
		}
	});
};

window.fullReindex = function() {
	frappe.confirm(
		__('This will reindex all files. This may take several minutes. Continue?'),
		function() {
			frappe.call({
				method: 'kgk_customisations.file_management.Utils.indexer.start_full_indexing',
				callback: function(r) {
					if (r.message) {
						frappe.show_alert({
							message: r.message.message,
							indicator: 'green'
						});
						setTimeout(() => location.reload(), 5000);
					}
				}
			});
		}
	);
};
