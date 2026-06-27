import { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import { getSuppliers, addSupplier, updateSupplier, deleteSupplier, getInventory, addInventory, updateInventory, deleteInventory } from '../lib/api';

export default function Database() {
  const [activeTab, setActiveTab] = useState<'suppliers' | 'inventory'>('suppliers');
  
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [inventory, setInventory] = useState<any[]>([]);

  // Supplier Form
  const [editingSupplierId, setEditingSupplierId] = useState<number | null>(null);
  const [supplierName, setSupplierName] = useState('');
  const [supplierRegion, setSupplierRegion] = useState('');
  const [supplierProducts, setSupplierProducts] = useState('');
  const [supplierEmail, setSupplierEmail] = useState('');
  
  // Inventory Form
  const [editingInventoryId, setEditingInventoryId] = useState<number | null>(null);
  const [invSupplierId, setInvSupplierId] = useState('');
  const [invProduct, setInvProduct] = useState('');
  const [invStock, setInvStock] = useState('0');
  const [invAvgDaily, setInvAvgDaily] = useState('0');
  const [invReorderLead, setInvReorderLead] = useState('0');
  const [invReorderThreshold, setInvReorderThreshold] = useState('0');

  useEffect(() => {
    fetchSuppliers();
    fetchInventory();
  }, []);

  const fetchSuppliers = async () => {
    const data = await getSuppliers();
    setSuppliers(data);
  };

  const fetchInventory = async () => {
    const data = await getInventory();
    setInventory(data);
  };

  const handleAddSupplier = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      name: supplierName,
      region: supplierRegion,
      products_supplied: supplierProducts,
      contact_email: supplierEmail
    };

    if (editingSupplierId) {
      await updateSupplier(editingSupplierId, payload);
      setEditingSupplierId(null);
    } else {
      await addSupplier(payload);
    }
    
    setSupplierName('');
    setSupplierRegion('');
    setSupplierProducts('');
    setSupplierEmail('');
    fetchSuppliers();
  };

  const handleEditSupplier = (supplier: any) => {
    setEditingSupplierId(supplier.id);
    setSupplierName(supplier.name);
    setSupplierRegion(supplier.region);
    setSupplierProducts(supplier.products_supplied);
    setSupplierEmail(supplier.contact_email || '');
    // Scroll up to form if needed
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleDeleteSupplier = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this supplier?')) return;
    await deleteSupplier(id);
    if (editingSupplierId === id) cancelEditSupplier();
    fetchSuppliers();
    fetchInventory(); // Keeps UI in sync after cascading inventory deletes
  };

  const cancelEditSupplier = () => {
    setEditingSupplierId(null);
    setSupplierName('');
    setSupplierRegion('');
    setSupplierProducts('');
    setSupplierEmail('');
  };

  const handleAddInventory = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      supplier_id: parseInt(invSupplierId),
      product: invProduct,
      stock_level: parseFloat(invStock),
      avg_daily_consumption: parseFloat(invAvgDaily),
      reorder_lead_time: parseInt(invReorderLead),
      reorder_threshold: parseFloat(invReorderThreshold)
    };

    if (editingInventoryId) {
      await updateInventory(editingInventoryId, payload);
      setEditingInventoryId(null);
    } else {
      await addInventory(payload);
    }
    
    setInvSupplierId('');
    setInvProduct('');
    setInvStock('0');
    setInvAvgDaily('0');
    setInvReorderLead('0');
    setInvReorderThreshold('0');
    fetchInventory();
  };

  const handleEditInventory = (inv: any) => {
    setEditingInventoryId(inv.id);
    setInvSupplierId(inv.supplier_id.toString());
    setInvProduct(inv.product);
    setInvStock(inv.stock_level.toString());
    setInvAvgDaily(inv.avg_daily_consumption.toString());
    setInvReorderLead(inv.reorder_lead_time.toString());
    setInvReorderThreshold(inv.reorder_threshold.toString());
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleDeleteInventory = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this inventory item?')) return;
    await deleteInventory(id);
    if (editingInventoryId === id) cancelEditInventory();
    fetchInventory();
  };

  const cancelEditInventory = () => {
    setEditingInventoryId(null);
    setInvSupplierId('');
    setInvProduct('');
    setInvStock('0');
    setInvAvgDaily('0');
    setInvReorderLead('0');
    setInvReorderThreshold('0');
  };

  return (
    <div className="min-h-screen pb-12">
      <Navbar />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-zinc-50 tracking-tight">Database Management</h1>
          <p className="text-sm text-zinc-200 mt-2">Manage your suppliers and inventory.</p>
        </header>

        <div className="flex gap-4 mb-8">
          <button 
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'suppliers' ? 'bg-emerald-500 text-black' : 'bg-zinc-800 text-zinc-200 hover:bg-zinc-800'}`}
            onClick={() => setActiveTab('suppliers')}
          >
            Suppliers
          </button>
          <button 
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'inventory' ? 'bg-emerald-500 text-black' : 'bg-zinc-800 text-zinc-200 hover:bg-zinc-800'}`}
            onClick={() => setActiveTab('inventory')}
          >
            Inventory
          </button>
        </div>

        {activeTab === 'suppliers' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-1">
              <div className="bg-zinc-700 shadow-sm border border-zinc-500 rounded-2xl hover:shadow-md transition-all p-6 rounded-xl border border-zinc-500">
                <h2 className="text-xl font-bold text-zinc-50 mb-4">{editingSupplierId ? 'Edit Supplier' : 'Add Supplier'}</h2>
                <form onSubmit={handleAddSupplier} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-zinc-300 mb-1">Name</label>
                    <input type="text" value={supplierName} onChange={(e) => setSupplierName(e.target.value)} required className="w-full bg-zinc-800 border border-zinc-500 rounded px-3 py-2 text-sm text-zinc-50 focus:outline-none focus:border-emerald-600/50" />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-zinc-300 mb-1">Region</label>
                    <input type="text" value={supplierRegion} onChange={(e) => setSupplierRegion(e.target.value)} required className="w-full bg-zinc-800 border border-zinc-500 rounded px-3 py-2 text-sm text-zinc-50 focus:outline-none focus:border-emerald-600/50" />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-zinc-300 mb-1">Products Supplied (CSV)</label>
                    <input type="text" value={supplierProducts} onChange={(e) => setSupplierProducts(e.target.value)} required className="w-full bg-zinc-800 border border-zinc-500 rounded px-3 py-2 text-sm text-zinc-50 focus:outline-none focus:border-emerald-600/50" />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-zinc-300 mb-1">Contact Email</label>
                    <input type="email" value={supplierEmail} onChange={(e) => setSupplierEmail(e.target.value)} className="w-full bg-zinc-800 border border-zinc-500 rounded px-3 py-2 text-sm text-zinc-50 focus:outline-none focus:border-emerald-600/50" />
                  </div>
                  <div className="flex gap-2 mt-4">
                    <button type="submit" className="flex-1 bg-emerald-500 text-black font-semibold py-2 rounded hover:bg-emerald-500/90 transition-colors">
                      {editingSupplierId ? 'Update' : 'Add'}
                    </button>
                    {editingSupplierId && (
                      <button type="button" onClick={cancelEditSupplier} className="flex-1 bg-zinc-800 text-zinc-900 font-semibold py-2 rounded hover:bg-zinc-800 transition-colors">
                        Cancel
                      </button>
                    )}
                  </div>
                </form>
              </div>
            </div>
            <div className="lg:col-span-2">
              <div className="bg-zinc-700 shadow-sm border border-zinc-500 rounded-2xl hover:shadow-md transition-all overflow-hidden rounded-xl border border-zinc-500">
                <table className="w-full text-left text-sm text-zinc-200">
                  <thead className="bg-zinc-800 border-b border-zinc-500 text-zinc-300 uppercase">
                    <tr>
                      <th className="px-6 py-3 font-semibold">ID</th>
                      <th className="px-6 py-3 font-semibold">Name</th>
                      <th className="px-6 py-3 font-semibold">Region</th>
                      <th className="px-6 py-3 font-semibold">Products</th>
                      <th className="px-6 py-3 font-semibold">Status</th>
                      <th className="px-6 py-3 font-semibold text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {suppliers.map(s => (
                      <tr key={s.id} className="hover:bg-zinc-800">
                        <td className="px-6 py-4">{s.id}</td>
                        <td className="px-6 py-4 text-zinc-50 font-medium">{s.name}</td>
                        <td className="px-6 py-4">{s.region}</td>
                        <td className="px-6 py-4">{s.products_supplied}</td>
                        <td className="px-6 py-4">
                          <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider ${s.status === 'active' ? 'bg-success/20 text-success' : 'bg-warning/20 text-warning'}`}>
                            {s.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <button onClick={() => handleEditSupplier(s)} className="text-emerald-400 hover:text-zinc-50 mr-3 text-xs font-semibold transition-colors">Edit</button>
                          <button onClick={() => handleDeleteSupplier(s.id)} className="text-danger hover:text-zinc-50 text-xs font-semibold transition-colors">Delete</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'inventory' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-1">
              <div className="bg-zinc-700 shadow-sm border border-zinc-500 rounded-2xl hover:shadow-md transition-all p-6 rounded-xl border border-zinc-500">
                <h2 className="text-xl font-bold text-zinc-50 mb-4">{editingInventoryId ? 'Edit Inventory' : 'Add Inventory'}</h2>
                <form onSubmit={handleAddInventory} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-zinc-300 mb-1">Supplier</label>
                    <select value={invSupplierId} onChange={(e) => setInvSupplierId(e.target.value)} required className="w-full bg-zinc-800 border border-zinc-500 rounded px-3 py-2 text-sm text-zinc-50 focus:outline-none focus:border-emerald-600/50">
                      <option value="">Select a supplier</option>
                      {suppliers.map(s => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-zinc-300 mb-1">Product</label>
                    <input type="text" value={invProduct} onChange={(e) => setInvProduct(e.target.value)} required className="w-full bg-zinc-800 border border-zinc-500 rounded px-3 py-2 text-sm text-zinc-50 focus:outline-none focus:border-emerald-600/50" />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-zinc-300 mb-1">Stock Level</label>
                      <input type="number" step="0.1" value={invStock} onChange={(e) => setInvStock(e.target.value)} required className="w-full bg-zinc-800 border border-zinc-500 rounded px-3 py-2 text-sm text-zinc-50 focus:outline-none focus:border-emerald-600/50" />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-zinc-300 mb-1">Avg Daily Cons.</label>
                      <input type="number" step="0.1" value={invAvgDaily} onChange={(e) => setInvAvgDaily(e.target.value)} required className="w-full bg-zinc-800 border border-zinc-500 rounded px-3 py-2 text-sm text-zinc-50 focus:outline-none focus:border-emerald-600/50" />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-zinc-300 mb-1">Lead Time (days)</label>
                      <input type="number" value={invReorderLead} onChange={(e) => setInvReorderLead(e.target.value)} required className="w-full bg-zinc-800 border border-zinc-500 rounded px-3 py-2 text-sm text-zinc-50 focus:outline-none focus:border-emerald-600/50" />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-zinc-300 mb-1">Threshold</label>
                      <input type="number" step="0.1" value={invReorderThreshold} onChange={(e) => setInvReorderThreshold(e.target.value)} required className="w-full bg-zinc-800 border border-zinc-500 rounded px-3 py-2 text-sm text-zinc-50 focus:outline-none focus:border-emerald-600/50" />
                    </div>
                  </div>
                  <div className="flex gap-2 mt-4">
                    <button type="submit" className="flex-1 bg-emerald-500 text-black font-semibold py-2 rounded hover:bg-emerald-500/90 transition-colors">
                      {editingInventoryId ? 'Update' : 'Add'}
                    </button>
                    {editingInventoryId && (
                      <button type="button" onClick={cancelEditInventory} className="flex-1 bg-zinc-800 text-zinc-900 font-semibold py-2 rounded hover:bg-zinc-800 transition-colors">
                        Cancel
                      </button>
                    )}
                  </div>
                </form>
              </div>
            </div>
            <div className="lg:col-span-2">
              <div className="bg-zinc-700 shadow-sm border border-zinc-500 rounded-2xl hover:shadow-md transition-all overflow-hidden rounded-xl border border-zinc-500">
                <table className="w-full text-left text-sm text-zinc-200">
                  <thead className="bg-zinc-800 border-b border-zinc-500 text-zinc-300 uppercase">
                    <tr>
                      <th className="px-6 py-3 font-semibold">ID</th>
                      <th className="px-6 py-3 font-semibold">Supplier</th>
                      <th className="px-6 py-3 font-semibold">Product</th>
                      <th className="px-6 py-3 font-semibold">Stock</th>
                      <th className="px-6 py-3 font-semibold">Lead/Threshold</th>
                      <th className="px-6 py-3 font-semibold text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {inventory.map(inv => {
                      const supplier = suppliers.find(s => s.id === inv.supplier_id);
                      return (
                        <tr key={inv.id} className="hover:bg-zinc-800">
                          <td className="px-6 py-4">{inv.id}</td>
                          <td className="px-6 py-4 text-zinc-50 font-medium">{supplier ? supplier.name : inv.supplier_id}</td>
                          <td className="px-6 py-4 text-accent-cyan font-medium">{inv.product}</td>
                          <td className="px-6 py-4">
                            {inv.stock_level} 
                            <span className="text-zinc-300 ml-1 text-xs">({inv.avg_daily_consumption}/day)</span>
                          </td>
                          <td className="px-6 py-4 text-xs text-zinc-300">
                            {inv.reorder_lead_time} days / {inv.reorder_threshold} thr.
                          </td>
                          <td className="px-6 py-4 text-right">
                            <button onClick={() => handleEditInventory(inv)} className="text-emerald-400 hover:text-zinc-50 mr-3 text-xs font-semibold transition-colors">Edit</button>
                            <button onClick={() => handleDeleteInventory(inv.id)} className="text-danger hover:text-zinc-50 text-xs font-semibold transition-colors">Delete</button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
