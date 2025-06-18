"use client"

import type React from "react"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Play, Download, Copy, Maximize2, Minimize2, Database, X, Loader2 } from "lucide-react"
import CodeMirror from "@uiw/react-codemirror"
import { sql } from "@codemirror/lang-sql"
import { vscodeDark } from "@uiw/codemirror-theme-vscode"
import { basicLight } from "@uiw/codemirror-theme-basic"
import { useTheme } from "next-themes"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable"
import { useMobile } from "@/hooks/use-mobile"
import Script from "next/script"
import { cn } from "@/lib/utils"

// Type definition for SQL.js
type SQLJSStatic = any;
type SQLJSDatabase = any;

// Add window interface for SQL.js
declare global {
  interface Window {
    initSqlJs: (config: { locateFile: (file: string) => string }) => Promise<SQLJSStatic>;
  }
}

// Initialize SQL.js with the correct configuration for browser environment
const initSqlJs = async () => {
  const SQL = await window.initSqlJs({
    locateFile: file => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.8.0/${file}`
  });
  return SQL;
};

interface SqlPlaygroundProps {
  className?: string
  onClose?: () => void
}

export function SqlPlayground({ className, onClose }: SqlPlaygroundProps) {
  const { theme } = useTheme()
  const [sqlQuery, setSqlQuery] = useState("SELECT * FROM users LIMIT 10;")
  const [dbType, setDbType] = useState("sqlite")
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [isExecuting, setIsExecuting] = useState(false)
  const [results, setResults] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState("query")
  const isMobile = useMobile()
  const [sqlLoaded, setSqlLoaded] = useState(false)
  const [db, setDb] = useState<SQLJSDatabase | null>(null)
  const [initializing, setInitializing] = useState(true)
  const containerRef = useRef<HTMLDivElement>(null)

  // Script load handling
  const handleSqlJsLoad = () => {
    setSqlLoaded(true);
  };
  
  // Initialize the database when SQL.js is loaded
  useEffect(() => {
    let mounted = true;
    
    const initializeDb = async () => {
      if (!sqlLoaded) return;
      
      try {
        setInitializing(true);
        
        const SQL = await initSqlJs();
        
        if (!mounted) return;
        
        const database = new SQL.Database();
        
        // Sample data for users table
        const usersData = [
          { id: 1, name: 'Nguyễn Văn A', email: 'nguyenvana@example.com', age: 30 },
          { id: 2, name: 'Trần Thị B', email: 'tranthib@example.com', age: 24 },
          { id: 3, name: 'Lê Văn C', email: 'levanc@example.com', age: 35 },
          { id: 4, name: 'Phạm Thị D', email: 'phamthid@example.com', age: 28 },
          { id: 5, name: 'Hoàng Văn E', email: 'hoangvane@example.com', age: 42 }
        ];
        
        // Sample data for products table
        const productsData = [
          { product_id: 101, product_name: 'Laptop', price: 1200, stock: 50, category_id: 1 },
          { product_id: 102, product_name: 'Điện thoại', price: 800, stock: 120, category_id: 1 },
          { product_id: 103, product_name: 'Bàn phím', price: 75, stock: 200, category_id: 2 },
          { product_id: 104, product_name: 'Chuột', price: 25, stock: 300, category_id: 2 },
          { product_id: 105, product_name: 'Màn hình', price: 300, stock: 80, category_id: 1 }
        ];
        
        // Sample data for orders table
        const ordersData = [
          { order_id: 1, user_id: 1, product_id: 101, quantity: 1, order_date: '2023-01-15' },
          { order_id: 2, user_id: 2, product_id: 103, quantity: 2, order_date: '2023-01-16' },
          { order_id: 3, user_id: 1, product_id: 102, quantity: 1, order_date: '2023-02-01' },
          { order_id: 4, user_id: 3, product_id: 104, quantity: 3, order_date: '2023-02-05' },
          { order_id: 5, user_id: 4, product_id: 101, quantity: 1, order_date: '2023-02-10' }
        ];
        
        // Sample data for categories table
        const categoriesData = [
          { category_id: 1, category_name: 'Điện tử' },
          { category_id: 2, category_name: 'Phụ kiện máy tính' },
          { category_id: 3, category_name: 'Sách' }
        ];
        
        // Sample data for employees table
        const employeesData = [
          { employee_id: 1, first_name: 'Mai', last_name: 'Linh', department_id: 1, salary: 60000 },
          { employee_id: 2, first_name: 'Quang', last_name: 'Minh', department_id: 2, salary: 55000 },
          { employee_id: 3, first_name: 'Thanh', last_name: 'Tùng', department_id: 3, salary: 70000 },
          { employee_id: 4, first_name: 'Hương', last_name: 'Giang', department_id: 4, salary: 50000 }
        ];
        
        // Sample data for departments table
        const departmentsData = [
          { department_id: 1, department_name: 'Sales', location: 'Hanoi' },
          { department_id: 2, department_name: 'Marketing', location: 'HCM' },
          { department_id: 3, department_name: 'IT', location: 'Hanoi' },
          { department_id: 4, department_name: 'HR', location: 'Danang' }
        ];
        
        // Sample data for projects table
        const projectsData = [
          { project_id: 1, project_name: 'Website Redesign', start_date: '2023-03-01', end_date: '2023-06-30', department_id: 3 },
          { project_id: 2, project_name: 'Marketing Campaign', start_date: '2023-04-10', end_date: '2023-07-20', department_id: 2 },
          { project_id: 3, project_name: 'New Product Launch', start_date: '2023-05-01', end_date: '2023-09-30', department_id: 1 }
        ];
        
        // Sample data for customers table
        const customersData = [
          { customer_id: 1, customer_name: 'Công ty A', city: 'Hanoi', country: 'Vietnam' },
          { customer_id: 2, customer_name: 'Công ty B', city: 'HCM', country: 'Vietnam' },
          { customer_id: 3, customer_name: 'Công ty C', city: 'Danang', country: 'Vietnam' }
        ];

        // Create users table and insert data
        database.run("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, age INTEGER);");
        usersData.forEach(user => {
          database.run("INSERT INTO users (id, name, email, age) VALUES (?, ?, ?, ?);", [user.id, user.name, user.email, user.age]);
        });

        // Create products table and insert data
        database.run("CREATE TABLE products (product_id INTEGER PRIMARY KEY, product_name TEXT, price REAL, stock INTEGER, category_id INTEGER);");
        productsData.forEach(product => {
          database.run("INSERT INTO products (product_id, product_name, price, stock, category_id) VALUES (?, ?, ?, ?, ?);", 
            [product.product_id, product.product_name, product.price, product.stock, product.category_id]);
        });

        // Create orders table and insert data
        database.run("CREATE TABLE orders (order_id INTEGER PRIMARY KEY, user_id INTEGER, product_id INTEGER, quantity INTEGER, order_date TEXT);");
        ordersData.forEach(order => {
          database.run("INSERT INTO orders (order_id, user_id, product_id, quantity, order_date) VALUES (?, ?, ?, ?, ?);", 
            [order.order_id, order.user_id, order.product_id, order.quantity, order.order_date]);
        });

        // Create categories table and insert data
        database.run("CREATE TABLE categories (category_id INTEGER PRIMARY KEY, category_name TEXT);");
        categoriesData.forEach(category => {
          database.run("INSERT INTO categories (category_id, category_name) VALUES (?, ?);", 
            [category.category_id, category.category_name]);
        });

        // Create employees table and insert data
        database.run("CREATE TABLE employees (employee_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, department_id INTEGER, salary REAL);");
        employeesData.forEach(employee => {
          database.run("INSERT INTO employees (employee_id, first_name, last_name, department_id, salary) VALUES (?, ?, ?, ?, ?);", 
            [employee.employee_id, employee.first_name, employee.last_name, employee.department_id, employee.salary]);
        });

        // Create departments table and insert data
        database.run("CREATE TABLE departments (department_id INTEGER PRIMARY KEY, department_name TEXT, location TEXT);");
        departmentsData.forEach(dept => {
          database.run("INSERT INTO departments (department_id, department_name, location) VALUES (?, ?, ?);", 
            [dept.department_id, dept.department_name, dept.location]);
        });

        // Create projects table and insert data
        database.run("CREATE TABLE projects (project_id INTEGER PRIMARY KEY, project_name TEXT, start_date TEXT, end_date TEXT, department_id INTEGER);");
        projectsData.forEach(project => {
          database.run("INSERT INTO projects (project_id, project_name, start_date, end_date, department_id) VALUES (?, ?, ?, ?, ?);", 
            [project.project_id, project.project_name, project.start_date, project.end_date, project.department_id]);
        });

        // Create customers table and insert data
        database.run("CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, customer_name TEXT, city TEXT, country TEXT);");
        customersData.forEach(customer => {
          database.run("INSERT INTO customers (customer_id, customer_name, city, country) VALUES (?, ?, ?, ?);", 
            [customer.customer_id, customer.customer_name, customer.city, customer.country]);
        });

        setDb(database);
      } catch (err: any) {
        console.error("Database initialization error:", err);
        setError(`Lỗi khi khởi tạo cơ sở dữ liệu: ${err.message}`);
      } finally {
        if (mounted) {
          setInitializing(false);
        }
      }
    };

    initializeDb();
    
    return () => {
      mounted = false;
      // Clean up database if needed
      if (db) {
        try {
          db.close();
        } catch (e) {
          console.error("Error closing database:", e);
        }
      }
    };
  }, [sqlLoaded]);

  // Mẫu dữ liệu kết quả
  const sampleResults = {
    columns: ["id", "name", "email", "created_at"],
    rows: [
      { id: 1, name: "Nguyễn Văn A", email: "nguyenvana@example.com", created_at: "2023-01-15" },
      { id: 2, name: "Trần Thị B", email: "tranthib@example.com", created_at: "2023-02-20" },
      { id: 3, name: "Lê Văn C", email: "levanc@example.com", created_at: "2023-03-10" },
      { id: 4, name: "Phạm Thị D", email: "phamthid@example.com", created_at: "2023-04-05" },
      { id: 5, name: "Hoàng Văn E", email: "hoangvane@example.com", created_at: "2023-05-12" },
    ],
    executionTime: "120ms",
    rowCount: 5,
  }

  const handleExecuteQuery = () => {
    setIsExecuting(true);
    setError(null);

    if (!db) {
      setError("Cơ sở dữ liệu chưa được khởi tạo. Vui lòng đợi trong giây lát.");
      setIsExecuting(false);
      return;
    }

    const query = sqlQuery.trim();
    if (!query) {
      setError("Vui lòng nhập câu lệnh SQL.");
      setIsExecuting(false);
      return;
    }

    try {
      // Measure execution time
      const startTime = performance.now();
      
      // Execute the SQL statement
      const res = db.exec(query);
      
      const endTime = performance.now();
      const executionTime = `${Math.round(endTime - startTime)}ms`;

      if (res.length === 0) {
        // If no results (e.g., INSERT, UPDATE, DELETE)
        setResults({
          columns: [],
          rows: [],
          executionTime,
          rowCount: 0,
          message: 'Câu lệnh đã được thực thi thành công (không có kết quả trả về).'
        });
      } else {
        // Process SELECT query results
        const result = res[0]; // Get the first result (if multiple statements)
        const columns = result.columns;
        const values = result.values;

        // Convert array values to object rows
        const rows = values.map((row: unknown[]) => {
          const rowObj: Record<string, unknown> = {};
          columns.forEach((col: string, index: number) => {
            rowObj[col] = row[index];
          });
          return rowObj;
        });

        setResults({
          columns,
          rows,
          executionTime,
          rowCount: rows.length
        });
      }
    } catch (error: any) {
      let errorMessage = `Lỗi SQL: ${error.message}`;
      if (error.message.includes("no such table:")) {
        errorMessage += "<br>Gợi ý: Vui lòng kiểm tra lại tên bảng. Các bảng hiện có là: <code>users</code>, <code>products</code>, <code>orders</code>, <code>categories</code>, <code>employees</code>, <code>departments</code>, <code>projects</code>, và <code>customers</code>.";
      }
      setError(errorMessage);
      console.error("SQL Execution Error:", error);
    } finally {
      setIsExecuting(false);
      
      // Chuyển sang tab kết quả sau khi thực thi truy vấn
      if (activeTab === "query") {
        setActiveTab("results");
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      handleExecuteQuery()
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen)
  }

  // CSS tùy chỉnh để loại bỏ viền focus
  const customSqlEditorStyles = `
    .cm-editor {
      outline: none !important;
      border-radius: 0.375rem;
      border: 1px solid #e2e8f0;
      overflow: hidden;
    }
    .cm-editor.cm-focused {
      outline: none !important;
      box-shadow: none !important;
      border: 1px solid #e2e8f0;
    }
    .cm-line {
      padding-left: 10px !important;
    }
    .cm-gutters {
      background-color: #f8fafc !important;
      border-right: 1px solid #e2e8f0 !important;
    }
    .cm-lineNumbers .cm-gutterElement {
      padding: 0 10px 0 5px !important;
    }
    .cm-scroller {
      overflow: auto;
    }
  `

  const renderQueryEditor = () => (
    <div className="sql-editor w-full h-full">
      <style jsx global>{customSqlEditorStyles}</style>
      <CodeMirror
        value={sqlQuery}
        height="200px"
        extensions={[sql()]}
        onChange={setSqlQuery}
        theme={theme === "dark" ? vscodeDark : basicLight}
        className="rounded-md overflow-hidden"
      />
    </div>
  )

  const renderResults = () => {
    if (initializing) {
      return (
        <div className="flex items-center justify-center p-4 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin mr-2" />
          <span>Đang khởi tạo cơ sở dữ liệu SQLite...</span>
        </div>
      )
    }
    
    if (isExecuting) {
      return (
        <div className="flex items-center justify-center p-4 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin mr-2" />
          <span>Đang thực thi truy vấn...</span>
        </div>
      )
    }

    if (error) {
      return (
        <div className="p-4 bg-destructive/10 text-destructive rounded-md" 
             dangerouslySetInnerHTML={{ __html: error }} />
      )
    }

    if (results) {
      return (
        <div className="h-full flex flex-col">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              Thời gian thực thi: <span className="font-medium">{results.executionTime}</span>
            </div>
            <Badge variant="outline" className="bg-success/10 text-success">
              {results.rowCount} dòng
            </Badge>
          </div>

          {results.message ? (
            <div className="p-4 bg-muted rounded-md text-foreground">
              {results.message}
            </div>
          ) : (
            <div className="overflow-hidden flex-1 border rounded-md">
              <div className="w-full h-full overflow-auto">
                <table className="sql-result-table w-full">
                  <thead className="sticky top-0 bg-background z-10">
                    <tr>
                      {results.columns.map((column: string, index: number) => (
                        <th 
                          key={column} 
                          className="min-w-0 truncate border-b bg-muted" 
                          title={column}
                          style={{ width: `${100 / results.columns.length}%` }}
                        >
                          {column}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {results.rows.length === 0 ? (
                      <tr>
                        <td colSpan={results.columns.length} className="text-center text-muted-foreground py-8">
                          Không tìm thấy dữ liệu.
                        </td>
                      </tr>
                    ) : (
                      results.rows.map((row: any, index: number) => (
                        <tr key={index} className="hover:bg-muted/50">
                          {results.columns.map((column: string, colIndex: number) => {
                            const value = row[column] !== undefined && row[column] !== null 
                              ? String(row[column]) 
                              : 'NULL';
                            return (
                              <td 
                                key={`${index}-${column}`} 
                                className="min-w-0 truncate px-2 py-1.5 text-sm border-b" 
                                title={value}
                                style={{ width: `${100 / results.columns.length}%` }}
                              >
                                <span className="block truncate">
                                  {value}
                                </span>
                              </td>
                            );
                          })}
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )
    }

    return (
      <div className="flex flex-col items-center justify-center h-[200px] text-muted-foreground gap-2">
        <Database className="h-10 w-10 text-muted-foreground/50" />
        <p>Chưa có kết quả. Hãy thực thi truy vấn.</p>
        <p className="text-xs text-muted-foreground/70">
          Các bảng có sẵn: users, products, orders, categories, employees, departments, projects, customers
        </p>
      </div>
    )
  }

  return (
    <div
      className={cn(
        "sql-playground flex flex-col h-full transition-all duration-300",
        isFullscreen ? "fixed inset-0 z-50 bg-background p-4" : "",
        className
      )}
      onKeyDown={handleKeyDown}
    >
      {/* SQL.js Script */}
      <Script 
        src="https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.8.0/sql-wasm.js"
        onLoad={handleSqlJsLoad}
        strategy="lazyOnload"
      />
      
      <Card className="flex flex-col h-full shadow-card border-border/50">
        <CardHeader className="px-4 py-3 border-b flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5 text-sql" />
              <CardTitle className="text-base font-medium">SQL Playground</CardTitle>
              <Badge variant="outline" className="ml-2 text-xs font-normal">
                SQLite (sql.js)
              </Badge>
            </div>
            <div className="flex items-center gap-1">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={toggleFullscreen}>
                      {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{isFullscreen ? "Thu nhỏ" : "Toàn màn hình"}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>

              {onClose && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onClose}>
                        <X className="h-4 w-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Đóng</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
          </div>
        </CardHeader>

        <div className="flex items-center gap-2 px-4 py-2 border-b bg-muted/30">
          <Button
            size="sm"
            className="h-8 bg-sql hover:bg-sql/90 text-sql-foreground gap-1"
            onClick={handleExecuteQuery}
            disabled={isExecuting || initializing}
          >
            {isExecuting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            <span>
              {initializing 
                ? "Đang khởi tạo..." 
                : isExecuting 
                  ? "Đang thực thi..." 
                  : "Chạy"}
            </span>
          </Button>

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button 
                  variant="outline" 
                  size="icon" 
                  className="h-8 w-8 ml-auto"
                  onClick={() => copyToClipboard(sqlQuery)}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Sao chép truy vấn</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          {results && results.rows && results.rows.length > 0 && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button 
                    variant="outline" 
                    size="icon" 
                    className="h-8 w-8"
                    onClick={() => {
                      // Simple CSV export
                      const headers = results.columns.join(',');
                      const rows = results.rows.map((row: any) => 
                        results.columns.map((col: string) => 
                          `"${row[col] !== null && row[col] !== undefined ? row[col] : ''}"`
                        ).join(',')
                      ).join('\n');
                      const csv = `${headers}\n${rows}`;
                      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
                      const url = URL.createObjectURL(blob);
                      const link = document.createElement('a');
                      link.setAttribute('href', url);
                      link.setAttribute('download', 'sql_results.csv');
                      link.style.visibility = 'hidden';
                      document.body.appendChild(link);
                      link.click();
                      document.body.removeChild(link);
                    }}
                  >
                    <Download className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Tải xuống kết quả (CSV)</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>

        <div className="flex-1 flex flex-col overflow-hidden p-4">
          {isFullscreen ? (
            // Desktop fullscreen - Split view
            <ResizablePanelGroup direction="horizontal" className="flex-1">
              <ResizablePanel defaultSize={50} minSize={30} className="pr-2">
                <div className="h-full flex flex-col">
                  <h3 className="text-sm font-medium mb-2 text-muted-foreground">Truy vấn SQL</h3>
                  <div className="flex-1">
                    {renderQueryEditor()}
                  </div>
                </div>
              </ResizablePanel>
              <ResizableHandle withHandle />
              <ResizablePanel defaultSize={50} minSize={30} className="pl-2">
                <div className="h-full flex flex-col">
                  <h3 className="text-sm font-medium mb-2 text-muted-foreground">Kết quả</h3>
                  <div className="flex-1 overflow-hidden">
                    {renderResults()}
                  </div>
                </div>
              </ResizablePanel>
            </ResizablePanelGroup>
          ) : (
            // Normal view with tabs
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full flex-1 flex flex-col">
              <TabsList className="grid grid-cols-2 w-full max-w-[260px] rounded-md bg-muted h-10">
                <TabsTrigger value="query" className="rounded-sm text-sm">
                  Truy vấn
                </TabsTrigger>
                <TabsTrigger value="results" className="rounded-sm text-sm">
                  {results ? `Kết quả (${results.rowCount} dòng)` : "Kết quả"}
                </TabsTrigger>
              </TabsList>
              <div className="flex-1 overflow-auto mt-4">
                <TabsContent value="query" className="m-0 h-full data-[state=active]:flex data-[state=inactive]:hidden">
                  {renderQueryEditor()}
                </TabsContent>
                <TabsContent value="results" className="m-0 h-full data-[state=active]:flex data-[state=inactive]:hidden">
                  {renderResults()}
                </TabsContent>
              </div>
            </Tabs>
          )}
        </div>

        <CardFooter className="px-4 py-2 border-t flex justify-between items-center">
          <div className="text-xs text-muted-foreground">
            Nhấn <kbd className="px-1 py-0.5 bg-muted rounded text-xs">Ctrl</kbd> +{" "}
            <kbd className="px-1 py-0.5 bg-muted rounded text-xs">Enter</kbd> để thực thi
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${initializing ? "bg-amber-500" : db ? "bg-success" : "bg-destructive"}`}></div>
            <span className="text-xs text-muted-foreground">
              {initializing ? "Đang khởi tạo" : db ? "Đã kết nối" : "Chưa kết nối"}
            </span>
          </div>
        </CardFooter>
      </Card>
    </div>
  )
}
