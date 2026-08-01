import { NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

export async function GET() {
  try {
    const dbPath = path.resolve(process.cwd(), '../metrics.db');
    
    if (!fs.existsSync(dbPath)) {
      return NextResponse.json({ error: "No metrics database found." }, { status: 404 });
    }

    const db = new Database(dbPath, { fileMustExist: true });
    
    // Group by category
    const categoryQuery = db.prepare("SELECT category, SUM(count) as total FROM metrics GROUP BY category");
    const categoryData = categoryQuery.all();

    // Group by subcategory
    const subcategoryQuery = db.prepare("SELECT subcategory as name, SUM(count) as total FROM metrics GROUP BY subcategory");
    const subcategoryData = subcategoryQuery.all();

    db.close();

    return NextResponse.json({
      categories: categoryData,
      breakdown: subcategoryData
    });

  } catch (error: any) {
    console.error("SQLite Error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
