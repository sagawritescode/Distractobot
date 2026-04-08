let allThoughts = [];

document.addEventListener('DOMContentLoaded', () => {
    // Set default dates in UI (last 7 days to today)
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - 7);
    
    document.getElementById('startDate').value = start.toISOString().split('T')[0];
    document.getElementById('endDate').value = end.toISOString().split('T')[0];

    fetchThoughts();
    fetchListTypes();
    
    // Event listeners
    document.getElementById('applyFiltersBtn').addEventListener('click', fetchThoughts);
    document.getElementById('searchInput').addEventListener('keyup', (e) => {
        if(e.key === 'Enter') fetchThoughts();
    });
});

async function fetchListTypes() {
    try {
        const response = await fetch('/api/list_types');
        const types = await response.json();
        const autocompleteList = document.getElementById('autocompleteList');
        if (autocompleteList) {
            autocompleteList.innerHTML = '';
            types.forEach(t => {
                const div = document.createElement('div');
                div.className = 'autocomplete-item';
                div.textContent = t;
                div.addEventListener('click', () => {
                    document.getElementById('listType').value = t;
                    closeAutocomplete();
                });
                autocompleteList.appendChild(div);
            });
        }
    } catch (error) {
        console.error('Error fetching list types:', error);
    }
}

function closeAutocomplete() {
    const list = document.getElementById('autocompleteList');
    if (list) list.classList.add('hidden');
}

function openAutocomplete() {
    const list = document.getElementById('autocompleteList');
    if (list) list.classList.remove('hidden');
}

// Close autocomplete when clicking outside
document.addEventListener('click', function (e) {
    if (!e.target.closest('.autocomplete')) {
        closeAutocomplete();
    }
});

// Filter autocomplete items as user types
document.getElementById('listType').addEventListener('input', function () {
    const filter = this.value.toLowerCase();
    const items = document.querySelectorAll('#autocompleteList .autocomplete-item');
    let anyVisible = false;
    items.forEach(item => {
        const txt = item.textContent.toLowerCase();
        if (txt.includes(filter)) {
            item.style.display = '';
            anyVisible = true;
        } else {
            item.style.display = 'none';
        }
    });
    if (anyVisible) openAutocomplete(); else closeAutocomplete();
});

async function fetchThoughts() {
    const search = document.getElementById('searchInput').value;
    const status = document.getElementById('statusFilter').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    const params = new URLSearchParams();
    if(search) params.append('search', search);
    if(status) params.append('status', status);
    if(startDate) params.append('start_date', startDate);
    if(endDate) params.append('end_date', endDate);

    try {
        const response = await fetch(`/api/thoughts?${params.toString()}`);
        const data = await response.json();
        allThoughts = data;
        renderTable(data);
    } catch (error) {
        console.error('Error fetching thoughts:', error);
        showToast('Error loading data', true);
    }
}

function renderTable(data) {
    const tableBody = document.getElementById('tableBody');
    tableBody.innerHTML = '';

    if (data.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-secondary);">No distractions found.</td></tr>';
        return;
    }

    data.forEach(thought => {
        const tr = document.createElement('tr');
        tr.className = `status-${thought.status}`;
        
        // Format date
        const dateObj = new Date(thought.timestamp + 'Z'); // Explicitly treat as UTC if required or assumed
        const localDate = new Date(thought.timestamp); // Use whatever parses best based on sqlite default
        
        tr.innerHTML = `
            <td>${localDate.toLocaleString()}</td>
            <td>${thought.intent || '-'}</td>
            <td>${thought.source || '-'}</td>
            <td class="summary-cell">${thought.summary || '-'}</td>
            <td>
                <select class="status-select" onchange="updateStatus(${thought.id}, this)">
                    <option value="open" ${thought.status === 'open' ? 'selected' : ''}>Open</option>
                    <option value="rejected" ${thought.status === 'rejected' ? 'selected' : ''}>Rejected</option>
                    <option value="cleared" ${thought.status === 'cleared' ? 'selected' : ''}>Cleared</option>
                </select>
            </td>
            <td>
                <button class="assign-btn" onclick="assignAction(${thought.id}, this)" ${thought.status !== 'open' ? 'disabled' : ''}>
                    Assign to Actionable
                </button>
            </td>
        `;
        tableBody.appendChild(tr);
    });
}



async function updateStatus(id, selectElement) {
    const newStatus = selectElement.value;
    const tr = selectElement.closest('tr');
    const button = tr.querySelector('.assign-btn');
    
    try {
        const response = await fetch(`/api/thoughts/${id}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ status: newStatus })
        });

        if (response.ok) {
            showToast(`Status updated to ${newStatus}`);
            const thoughtIndex = allThoughts.findIndex(t => t.id === id);
            if (thoughtIndex !== -1) {
                allThoughts[thoughtIndex].status = newStatus;
            }
            tr.className = `status-${newStatus}`;
             button.disabled = (newStatus !== 'open');
        } else {
            showToast('Failed to update status', true);
            const thought = allThoughts.find(t => t.id === id);
            selectElement.value = thought.status;
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Error updating status', true);
    }
}

let currentActionableId = null;

// Event Listeners for Modal
document.addEventListener('DOMContentLoaded', () => {
    const cancelBtn = document.getElementById('cancelAssignBtn');
    const submitBtn = document.getElementById('submitAssignBtn');
    if (cancelBtn) cancelBtn.addEventListener('click', closeAssignModal);
    if (submitBtn) submitBtn.addEventListener('click', submitAssignment);
});

function assignAction(id, buttonElement) {
    currentActionableId = id;
    document.getElementById('listType').value = '';
    document.getElementById('subtype').value = '';
    document.getElementById('actionDetails').value = '';
    document.getElementById('actionDeadline').value = '';
    document.getElementById('assignModal').classList.remove('hidden');
    // Load latest list types and show them immediately
    fetchListTypes().then(() => {
        openAutocomplete();
    });
}

function closeAssignModal() {
    currentActionableId = null;
    document.getElementById('assignModal').classList.add('hidden');
}

async function submitAssignment() {
    if (!currentActionableId) return;

    const btn = document.getElementById('submitAssignBtn');
    btn.textContent = 'Submitting...';
    btn.disabled = true;

    const payload = {
        list_type: document.getElementById('listType').value || 'Uncategorized',
        subtype: document.getElementById('subtype').value || '',
        details: document.getElementById('actionDetails').value || '',
        deadline: document.getElementById('actionDeadline').value || null
    };

    try {
        const response = await fetch(`/api/thoughts/${currentActionableId}/assign`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const data = await response.json();
            showToast(data.message || 'Assigned successfully!');
            closeAssignModal();
            fetchThoughts(); // reload table to reflect "cleared" state
            fetchListTypes(); // reload datalist incase a new type was added
        } else {
            showToast('Failed to assign', true);
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Error assigning action', true);
    } finally {
        btn.textContent = 'Submit Assignment';
        btn.disabled = false;
    }
}

function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.style.backgroundColor = isError ? 'var(--danger-color)' : 'var(--success-color)';
    toast.classList.remove('hidden');
    
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}
