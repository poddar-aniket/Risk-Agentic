import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === 'GET') {
    try {
      const response = await fetch('http://localhost:8000/suppliers', { cache: 'no-store' });
      const data = await response.json();
      res.status(response.status).json(data);
    } catch (error) {
      res.status(500).json({ error: 'Failed to fetch suppliers' });
    }
  } else if (req.method === 'POST') {
    try {
      const response = await fetch('http://localhost:8000/suppliers', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(req.body),
      });
      const data = await response.json();
      res.status(response.status).json(data);
    } catch (error) {
      res.status(500).json({ error: 'Failed to create supplier' });
    }
  } else {
    res.setHeader('Allow', ['GET', 'POST']);
    res.status(405).end(`Method ${req.method} Not Allowed`);
  }
}
