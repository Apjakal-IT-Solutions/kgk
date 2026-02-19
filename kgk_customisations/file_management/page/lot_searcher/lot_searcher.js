frappe.pages['lot_searcher'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Lot Searcher',
		single_column: true
	});

	// Create the page content
	page.main.html(`
		<div class="lot-searcher-container" style="padding: 20px;">
			<div class="search-section" style="margin-bottom: 30px;">
				<div class="form-group">
					<label for="lot-id-input" style="font-weight: bold; font-size: 14px;">Lot ID</label>
					<div style="display: flex; gap: 10px; margin-top: 10px;">
						<input 
							type="text" 
							id="lot-id-input" 
							class="form-control" 
							placeholder="Enter Lot ID (e.g., 21156281)"
							style="max-width: 300px;"
						/>
						<button class="btn btn-primary" id="search-btn">
							<svg class="icon icon-sm" style="margin-right: 5px;">
								<use href="#icon-search"></use>
							</svg>
							Search
						</button>
					</div>
				</div>
			</div>

			<div id="results-section" style="display: none;">
				<hr style="margin: 30px 0;">

                <!-- Azure Video Results -->
				<div id="azure-video-results" style="margin-bottom: 40px;">
					<h4 style="margin-bottom: 20px; display: block; align-items: center; justify-content: flex-start;">
						<svg class="icon icon-sm" style="margin-right: 8px;">
							<use href="#icon-play"></use>
						</svg>
						Azure Videos
					</h4>
					<div class="azure-video-list" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px;"></div>
				</div>
				
				<!-- Video Results -->
				<div id="video-results" style="margin-bottom: 40px;">
					<h4 style="margin-bottom: 20px; display: block; align-items: center; justify-content: flex-start;">
						<svg class="icon icon-sm" style="margin-right: 8px;">
							<use href="#icon-play"></use>
						</svg>
						Videos
					</h4>
					<div class="video-list" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px;"></div>
				</div>

				<!-- Packet Scan Results -->
				<div id="packet-scan-results">
					<h4 style="margin-bottom: 20px; display: block; align-items: center; justify-content: flex-start;">
						<svg class="icon icon-sm" style="margin-right: 8px;">
							<use href="#icon-file"></use>
						</svg>
						Packet Scans
					</h4>
					<div class="packet-scan-list" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px;"></div>
				</div>

				<div id="no-results" style="display: none; padding: 40px; text-align: center; color: #888;">
					<p style="font-size: 16px;">No videos or packet scans found for this Lot ID</p>
				</div>
			</div>
			
			<style>
				.thumbnail-card {
					border: 1px solid #e0e0e0;
					border-radius: 8px;
					overflow: hidden;
					box-shadow: 0 2px 4px rgba(0,0,0,0.1);
					background: white;
				}
				.thumbnail-icon {
					position: relative;
				}
				.thumbnail-icon::before {
					content: '';
					display: block;
					padding-top: 0; /* Remove aspect ratio constraint for images */
				}
			</style>
		</div>
	`);

	// Event handlers
	const $input = page.main.find('#lot-id-input');
	const $searchBtn = page.main.find('#search-btn');
	const $resultsSection = page.main.find('#results-section');
	const $videoResults = page.main.find('#video-results');
    const $azureVideoResults = page.main.find('#azure-video-results');
	const $packetScanResults = page.main.find('#packet-scan-results');
	const $noResults = page.main.find('#no-results');

	// Search function
	function performSearch() {
		const lot_id = $input.val().trim();
		
		if (!lot_id) {
			frappe.msgprint('Please enter a Lot ID');
			return;
		}

		// Show loading state
		$searchBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" style="margin-right: 5px;"></span>Searching...');

		// Call backend search method
		frappe.call({
			method: 'kgk_customisations.file_management.page.lot_searcher.lot_searcher.search_lot',
			args: { lot_id: lot_id },
			callback: function(r) {
				if (r.message) {
					displayResults(r.message, lot_id);
				}
			},
			always: function() {
				// Reset button state
				$searchBtn.prop('disabled', false).html('<svg class="icon icon-sm" style="margin-right: 5px;"><use href="#icon-search"></use></svg>Search');
			}
		});
	}

	// Display results
	function displayResults(data, lot_id) {
		$resultsSection.show();

		// Clear previous results
		page.main.find('.video-list').empty();
		page.main.find('.packet-scan-list').empty();
        page.main.find('.azure-video-list').empty();

		if (!data.has_results) {
			$videoResults.hide();
			$packetScanResults.hide();
			$azureVideoResults.hide();
			$noResults.show();
			return;
		}

		$noResults.hide();

		// Display videos as grid
		const videos = data.videos || {};
		const videoTypes = [
			{ key: 'rough_video', label: 'Rough Video', icon: 'play', color: '#8B4513' },
			{ key: 'polish_video', label: 'Polish Video', icon: 'play', color: '#4169E1' },
			{ key: 'tension_video', label: 'Tension Video', icon: 'play', color: '#DC143C' },
            {key: 'azure_video', label: 'Azure Video', icon: 'play', color: '#28a745' },
		];

		let hasVideos = false;
		videoTypes.forEach(function(vt) {
			if (videos[vt.key]) {
				hasVideos = true;
				const fileName = videos[vt.key].split('/').pop();
				const videoPath = videos[vt.key];
				const thumbnailUrl = `/api/method/kgk_customisations.file_management.external_file_utils.serve_video_thumbnail?file_path=${encodeURIComponent(videoPath)}`;
				
				page.main.find('.video-list').append(`
					<div class="thumbnail-card view-file-btn" data-path="${videoPath}" style="cursor: pointer; transition: transform 0.2s, box-shadow 0.2s;">
						<div class="thumbnail-icon" style="background-image: url('${thumbnailUrl}'); background-size: contain; background-repeat: no-repeat; background-position: center; height: 120px; border-radius: 8px 8px 0 0; position: relative; background-color: #000;">
							<div style="position: absolute; top: 8px; right: 8px; background: rgba(${vt.color === '#8B4513' ? '139, 69, 19' : vt.color === '#4169E1' ? '65, 105, 225' : '220, 20, 60'}, 0.9); color: white; padding: 4px 8px; border-radius: 4px; font-size: 10px; font-weight: 600;">
								<svg class="icon icon-sm" style="width: 12px; height: 12px; vertical-align: middle;">
									<use href="#icon-play"></use>
								</svg>
							</div>
						</div>
						<div class="thumbnail-info" style="padding: 12px; background: white; border-radius: 0 0 8px 8px;">
							<div style="font-weight: 600; font-size: 14px; margin-bottom: 4px; color: #333;">${vt.label}</div>
							<div style="font-size: 11px; color: #888; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${fileName}">${fileName}</div>
						</div>
					</div>
				`);
			}
		});

		if (hasVideos) {
			$videoResults.show();
		} 
        else {
			$videoResults.hide();            
        }
        // render azure videos (always 1 for rough and 1 for polish), which are static url combined with lot_id so they will always be present even if the video doesn't exist
        const azureVideos = [
    {
        label: "Azure Rough Video",
        url: `https://storageweweb.blob.core.windows.net/files/INVENTORYDATA/DNA.html?id=${lot_id}-R`
    },
    {
        label: "Azure Polish Video",
        url: `https://storageweweb.blob.core.windows.net/files/INVENTORYDATA/DNA.html?id=${lot_id}`
    }
];

page.main.find('.azure-video-list').empty();
azureVideos.forEach(av => {
    page.main.find('.azure-video-list').append(`
        <div class="thumbnail-card view-file-btn" data-path="${av.url}" style="cursor: pointer; transition: transform 0.2s, box-shadow 0.2s;">
            <div class="thumbnail-icon" style="background-image: url('/assets/kgk_customisations/images/video_placeholder.png'); background-size: contain; background-repeat: no-repeat; background-position: center; height: 120px; border-radius: 8px 8px 0 0; position: relative; background-color: #000;">
                <div style="position: absolute; top: 8px; right: 8px; background: rgba(100, 20, 69, 0.9); color: white; padding: 4px 8px; border-radius: 4px; font-size: 10px; font-weight: 600;">
                    <svg class="icon icon-sm" style="width: 12px; height: 12px; vertical-align: middle;">
                        <use href="#icon-play"></use>
                    </svg>
                </div>
            </div>
            <div class="thumbnail-info" style="padding: 12px; background: white; border-radius: 0 0 8px 8px;">
                <div style="font-weight: 600; font-size: 14px; margin-bottom: 4px; color: #333;">${av.label}</div>
                <div style="font-size: 11px; color: #888; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${av.url}">${av.url.split('/').pop()}</div>
            </div>
        </div>
    `);
});
$azureVideoResults.show();
        $azureVideoResults.show();

		// Display packet scans as grid
		const packetScans = data.packet_scans || [];
		if (packetScans.length > 0) {
			packetScans.forEach(function(scanPath, index) {
				const fileName = scanPath.split('/').pop();
				const fileExt = fileName.split('.').pop().toLowerCase();
				let icon = 'file';
				let color = '#6c757d';
				let thumbnailContent = '';
				
				if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'].includes(fileExt)) {
					icon = 'image';
					color = '#28a745';
					// Use actual image as thumbnail
					const imageUrl = `/api/method/kgk_customisations.file_management.page.lot_searcher.lot_searcher.serve_file?file_path=${encodeURIComponent(scanPath)}`;
					thumbnailContent = `
						<div class="thumbnail-icon" style="background-image: url('${imageUrl}'); background-size: contain; background-repeat: no-repeat; background-position: center; height: 120px; border-radius: 8px 8px 0 0; position: relative; background-color: #f8f9fa;">
							<div style="position: absolute; top: 8px; right: 8px; background: rgba(40, 167, 69, 0.9); color: white; padding: 4px 8px; border-radius: 4px; font-size: 10px; font-weight: 600;">
								<svg class="icon icon-sm" style="width: 12px; height: 12px; vertical-align: middle;">
									<use href="#icon-${icon}"></use>
								</svg>
							</div>
						</div>
					`;
				} else if (fileExt === 'pdf') {
					icon = 'file-pdf';
					color = '#dc3545';
					// Use PDF thumbnail
					const thumbnailUrl = `/api/method/kgk_customisations.file_management.external_file_utils.serve_pdf_thumbnail?file_path=${encodeURIComponent(scanPath)}`;
					thumbnailContent = `
						<div class="thumbnail-icon" style="background-image: url('${thumbnailUrl}'); background-size: contain; background-repeat: no-repeat; background-position: center; height: 120px; border-radius: 8px 8px 0 0; position: relative; background-color: #f8f9fa;">
							<div style="position: absolute; top: 8px; right: 8px; background: rgba(220, 53, 69, 0.9); color: white; padding: 4px 8px; border-radius: 4px; font-size: 10px; font-weight: 600;">
								<svg class="icon icon-sm" style="width: 12px; height: 12px; vertical-align: middle;">
									<use href="#icon-${icon}"></use>
								</svg>
							</div>
						</div>
					`;
				} else {
					thumbnailContent = `
						<div class="thumbnail-icon" style="background: linear-gradient(135deg, ${color} 0%, ${color}dd 100%); display: flex; align-items: center; justify-content: center; height: 120px; border-radius: 8px 8px 0 0;">
							<svg class="icon" style="width: 48px; height: 48px; color: white;">
								<use href="#icon-${icon}"></use>
							</svg>
						</div>
					`;
				}

				page.main.find('.packet-scan-list').append(`
					<div class="thumbnail-card view-file-btn" data-path="${scanPath}" style="cursor: pointer; transition: transform 0.2s, box-shadow 0.2s;">
						${thumbnailContent}
						<div class="thumbnail-info" style="padding: 12px; background: white; border-radius: 0 0 8px 8px;">
							<div style="font-weight: 600; font-size: 14px; margin-bottom: 4px; color: #333;">Scan ${index + 1}</div>
							<div style="font-size: 11px; color: #888; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${fileName}">${fileName}</div>
						</div>
					</div>
				`);
			});
			$packetScanResults.show();
		} else {
			$packetScanResults.hide();
		}

		// Add hover effects and click handlers
		page.main.find('.thumbnail-card').hover(
			function() {
				$(this).css({
					'transform': 'translateY(-4px)',
					'box-shadow': '0 8px 16px rgba(0,0,0,0.15)'
				});
			},
			function() {
				$(this).css({
					'transform': 'translateY(0)',
					'box-shadow': '0 2px 4px rgba(0,0,0,0.1)'
				});
			}
		).on('click', function() {
			const filePath = $(this).data('path');
			openFile(filePath);
		});
	}

	// Open file in new tab
	function openFile(filePath) {
    if (/^https?:\/\//i.test(filePath)) {
        // External URL (like Azure)
        window.open(filePath, '_blank');
    } else {
        // Local file, serve via backend
        const url = `/api/method/kgk_customisations.file_management.page.lot_searcher.lot_searcher.serve_file?file_path=${encodeURIComponent(filePath)}`;
        window.open(url, '_blank');
    }
}

	// Event listeners
	$searchBtn.on('click', performSearch);
	$input.on('keypress', function(e) {
		if (e.which === 13) { // Enter key
			performSearch();
		}
	});

	// Focus on input
	$input.focus();
};
