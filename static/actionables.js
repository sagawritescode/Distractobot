document.addEventListener('DOMContentLoaded', () => {
    fetchActionables();
    
    // Event listeners
    document.getElementById('applyFiltersBtn').addEventListener('click', fetchActionables);
    document.getElementById('searchInput').addEventListener('keyup', (e) => {
        if(e.key === 'Enter') fetchActionables();
    });
});

async function fetchActionables() {
    const search = document.getElementById('searchInput').value;
    const listType = document.getElementById('listTypeFilter').value;
    const subtype = document.getElementById('subtypeFilter').value;
    
    const params = new URLSearchParams();
    if(search) params.append('search', search);
    if(listType) params.append('list_type', listType);
    if(subtype) params.append('subtype', subtype);

    try {
        const response = await fetch(`/api/actionables?${params.toString()}`);
        const data = await response.json();
        
        populateListTypes(data.list_types, listType);
        populateSubtypes(data.subtypes, subtype);
        renderTable(data.actionables);
    } catch (error) {
        console.error('Error fetching actionables:', error);
    }
}

function populateListTypes(types, currentSelection) {
    const select = document.getElementById('listTypeFilter');
    const existingValue = select.value;
    select.innerHTML = '<option value="">All Lists</option>';
    
    types.forEach(type => {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = type;
        if (type === currentSelection || type === existingValue) option.selected = true;
        select.appendChild(option);
    });
}

function populateSubtypes(subtypes, currentSelection) {
    const select = document.getElementById('subtypeFilter');
    const existingValue = select.value;
    select.innerHTML = '<option value="">All Subtypes</option>';
    
    subtypes.forEach(st => {
        const option = document.createElement('option');
        option.value = st;
        option.textContent = st;
        if (st === currentSelection || st === existingValue) option.selected = true;
        select.appendChild(option);
    });
}

function renderTable(data) {
    const tableBody = document.getElementById('tableBody');
    tableBody.innerHTML = '';

    if (data.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-secondary);">No actionables found.</td></tr>';
        return;
    }

    data.forEach(item => {
        const tr = document.createElement('tr');
        
        const createdDate = new Date(item.created_at + 'Z').toLocaleString();
        const deadlineDate = item.deadline ? new Date(item.deadline).toLocaleDateString() : '-';
        
        tr.innerHTML = `
            <td><span style="background: rgba(255,255,255,0.1); padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.85rem;">${item.list_type}</span></td>
            <td><span style="background: rgba(255,255,255,0.05); padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.85rem; color: var(--text-secondary);">${item.subtype || '-'}</span></td>
            <td class="summary-cell">${item.details || '-'}</td>
            <td class="summary-cell" style="color: var(--text-secondary);">${item.summary || '-'}</td>
            <td>${deadlineDate}</td>
            <td style="font-size:0.85rem; color: var(--text-secondary);">${createdDate}</td>
            <td><span class="status-select" style="border:none; background: var(--bg-color)">${item.status}</span></td>
        `;
        tableBody.appendChild(tr);
    });
}
